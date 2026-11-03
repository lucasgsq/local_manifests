import importlib.util
import io
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
import urllib.error
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('audit', HERE.parent / 'check-security-backports.py')
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


class BackportTests(unittest.TestCase):
    def setUp(self):
        # Fixtures are kept under this explicit workspace directory for inspection.
        self.root = Path(tempfile.mkdtemp(prefix='case-', dir=str(HERE))).resolve()
        self.repo = self.root / 'frameworks/base'
        self.repo.mkdir(parents=True)
        self.command('init', '-q')
        self.command('config', 'user.name', 'Quark test')
        self.command('config', 'user.email', 'test@example.invalid')
        self.first = self.commit('first', 'base')
        self.second = self.commit('second', 'fix')
        self.projects = {'LineageOS/android_frameworks_base': ['frameworks/base']}
        self.config = {'branch': 'lineage-18.1', 'topic_prefix': 'R', 'minimum_month': '2025-08'}

    def command(self, *args):
        return subprocess.check_output(['git', '-C', str(self.repo), *args], stderr=subprocess.PIPE).decode().strip()

    def commit(self, content, message):
        (self.repo / 'code.txt').write_text(content, encoding='utf-8')
        self.command('add', 'code.txt')
        self.command('-c', 'commit.gpgsign=false', 'commit', '-q', '-m', message)
        return self.command('rev-parse', 'HEAD')

    def change(self, sha, number=1, month='2026-10'):
        return {'_number': number, 'project': 'LineageOS/android_frameworks_base',
                'branch': 'lineage-18.1', 'status': 'MERGED',
                'current_revision': sha, 'topic': 'R_asb_' + month}

    def batches(self, changes, month='2026-10', pending=None):
        return {month: {'merged': changes, 'open': pending or []}}

    def verify(self, batches, projects=None):
        return audit.verify_batches(self.root, projects or self.projects, batches, '2025-08')

    def test_real_ancestry_verified(self):
        self.assertEqual(self.verify(self.batches([self.change(self.first)]))['month'], '2026-10')

    def test_full_audit_rechecks_clean_heads_before_credit(self):
        def loader(branch, prefix, status):
            return [self.change(self.first)] if status == 'merged' else []
        result = audit.perform(self.root, self.config, loader, lambda root: self.projects)
        self.assertEqual(result['month'], '2026-10')
        self.assertNotIn('error', result)

    def test_missing_older_fix_blocks_newer_month(self):
        data = {'2026-09': {'merged': [self.change('1' * 40, month='2026-09')], 'open': []},
                '2026-10': {'merged': [self.change(self.second, 2)], 'open': []}}
        self.assertEqual(self.verify(data)['month'], '')

    def test_newer_incomplete_batch_preserves_earlier_verified_reference(self):
        data = {'2026-09': {'merged': [self.change(self.first, month='2026-09')], 'open': []},
                '2026-10': {'merged': [self.change('1' * 40, 2)], 'open': []}}
        self.assertEqual(self.verify(data)['month'], '2026-09')

    def test_dirty_audited_source_is_not_credited(self):
        (self.repo / 'code.txt').write_text('uncommitted change')
        result = self.verify(self.batches([self.change(self.first)]))
        self.assertEqual(result['month'], '')
        self.assertEqual(result['checks'][0]['status'], 'local_changes_or_unresolved_conflicts')

    def test_local_revert_does_not_count_as_present_fix(self):
        self.command('-c', 'commit.gpgsign=false', 'revert', '--no-edit', self.second)
        result = self.verify(self.batches([self.change(self.second)]))
        self.assertEqual(result['month'], '')
        self.assertEqual(result['checks'][0]['status'], 'explicit_revert_requires_review')

    def test_existing_commit_on_unmerged_branch_is_not_credited(self):
        self.command('checkout', '-q', '-b', 'other')
        other = self.commit('other change', 'unmerged fix')
        self.command('checkout', '-q', '--detach', self.second)
        result = self.verify(self.batches([self.change(other)]))
        self.assertEqual(result['month'], '')
        self.assertEqual(result['checks'][0]['status'], 'not_ancestor_equivalence_not_assumed')

    def test_published_asb_revert_is_an_expected_upstream_transition(self):
        self.command('-c', 'commit.gpgsign=false', 'revert', '--no-edit', self.second)
        revert = self.command('rev-parse', 'HEAD')
        result = self.verify(self.batches([self.change(self.second), self.change(revert, 2)]))
        self.assertEqual(result['month'], '2026-10')

    def test_upstream_revert_in_later_month_does_not_permanently_block_that_month(self):
        self.command('-c', 'commit.gpgsign=false', 'revert', '--no-edit', self.second)
        revert = self.command('rev-parse', 'HEAD')
        data = {'2026-09': {'merged': [self.change(self.second, month='2026-09')], 'open': []},
                '2026-10': {'merged': [self.change(revert, 2)], 'open': []}}
        result = self.verify(data)
        self.assertEqual(result['month'], '2026-10')
        self.assertFalse(result['batches'][0]['complete'])

    def test_revert_published_for_another_repository_is_not_credited(self):
        self.command('-c', 'commit.gpgsign=false', 'revert', '--no-edit', self.second)
        revert = self.change(self.command('rev-parse', 'HEAD'), 2)
        revert['project'] = 'LineageOS/android_other'
        result = self.verify(self.batches([self.change(self.second), revert]))
        self.assertEqual(result['month'], '')
        self.assertEqual(result['checks'][0]['status'], 'explicit_revert_requires_review')

    def test_untracked_source_is_not_credited(self):
        (self.repo / 'extra.java').write_text('untracked source')
        result = self.verify(self.batches([self.change(self.first)]))
        self.assertEqual(result['month'], '')

    def test_fork_alias_resolves_by_repository_basename(self):
        projects = {'lucasgsq/android_frameworks_base': ['frameworks/base']}
        self.assertEqual(self.verify(self.batches([self.change(self.first)]), projects)['month'], '2026-10')

    def test_open_batch_is_not_credited(self):
        result = self.verify(self.batches([self.change(self.first)], pending=[self.change(self.second, 2)]))
        self.assertEqual(result['month'], '')

    def test_declared_missing_project_is_not_silently_skipped(self):
        result = self.verify(self.batches([self.change(self.first)]),
                             {'LineageOS/android_frameworks_base': ['absent']})
        self.assertEqual(result['checks'][0]['status'], 'declared_project_missing')
        self.assertEqual(result['month'], '')

    def test_project_outside_tree_is_rejected(self):
        with self.assertRaises(audit.Unverified):
            self.verify(self.batches([self.change(self.first)]),
                        {'LineageOS/android_frameworks_base': ['../outside']})

    def test_network_failure_clears_previous_month_and_writes_report(self):
        overlay = self.root / 'overlay'
        audit.write_overlay(overlay, '2026-10')
        def offline(*args):
            raise urllib.error.URLError('offline')
        report = audit.execute(self.root, overlay, self.root / 'report.json', self.config, offline)
        self.assertEqual(report['month'], '')
        value = ET.parse(overlay / audit.RESOURCE).find('string').text
        self.assertIn(value, [None, ''])
        self.assertIn('offline', json.loads((self.root / 'report.json').read_text())['error'])

    def test_pagination_fetches_every_page(self):
        first = self.change(self.first); first['_more_changes'] = True
        pages = [[first], [self.change(self.second, 2)]]
        seen = []
        def opener(request, timeout):
            seen.append(request.full_url)
            return io.BytesIO(b")]}'\n" + json.dumps(pages[len(seen) - 1]).encode())
        result = audit.query_changes('lineage-18.1', 'R', 'merged', opener)
        self.assertEqual(len(result), 2)
        self.assertIn('S=500', seen[1])

    def test_duplicate_page_is_unverified(self):
        change = self.change(self.first); change['_more_changes'] = True
        def opener(request, timeout):
            return io.BytesIO(b")]}'\n" + json.dumps([change]).encode())
        with self.assertRaises(audit.Unverified):
            audit.query_changes('lineage-18.1', 'R', 'merged', opener)

    def test_android_branches_cannot_share_results(self):
        wrong = dict(self.config, branch='lineage-19.1')
        with self.assertRaises(ValueError):
            audit.perform(self.root, wrong)

    def test_old_pixel_topic_does_not_invalidate_current_scope(self):
        old = self.change(self.first); old['topic'] = 'S_asb_2022-07_pixel'
        old['branch'] = 'lineage-19.1'
        new = self.change(self.second, 2); new['topic'] = 'S_asb_2026-10'
        new['branch'] = 'lineage-19.1'
        def loader(branch, prefix, status):
            return [old, new] if status == 'merged' else []
        self.assertEqual(list(audit.catalog('lineage-19.1', 'S', '2025-08', loader)), ['2026-10'])


if __name__ == '__main__':
    unittest.main(verbosity=2)

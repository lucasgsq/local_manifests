import contextlib
import importlib.util
import io
from pathlib import Path
import subprocess
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parent.parent / 'patches.py'
spec = importlib.util.spec_from_file_location('quark_patches', SCRIPT)
patches = importlib.util.module_from_spec(spec)
spec.loader.exec_module(patches)


def git(repo, *args):
    return subprocess.run(['git', '-C', str(repo), *args], check=True,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          encoding='utf-8').stdout.strip()


class AutomationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='quark-patches-')
        self.root = Path(self.tmp.name)
        (self.root / '.repo').mkdir()
        self.plan = []
        for name in ('media', 'display'):
            source = self.root / ('source-' + name)
            source.mkdir()
            git(source, 'init', '-b', 'patch-source')
            git(source, 'config', 'user.name', 'Patch automation test')
            git(source, 'config', 'user.email', 'test@example.invalid')
            git(source, 'config', 'commit.gpgsign', 'false')
            (source / 'feature.txt').write_text('base\n')
            git(source, 'add', '.')
            git(source, 'commit', '-m', 'base')
            base = git(source, 'rev-parse', 'HEAD')
            commits = []
            for number in range(1, 3):
                (source / 'feature.txt').write_text('feature {}\n'.format(number))
                git(source, 'commit', '-am', 'patch {}'.format(number))
                commits.append(git(source, 'rev-parse', 'HEAD'))
            target = self.root / name
            git(self.root, 'clone', str(source), str(target))
            git(target, 'checkout', '--detach', base)
            git(target, 'config', 'user.name', 'Patch automation test')
            git(target, 'config', 'user.email', 'test@example.invalid')
            git(target, 'config', 'commit.gpgsign', 'false')
            self.plan.append(dict(path=name, url=str(source), branch='patch-source', commits=commits))

    def tearDown(self):
        # Git files may be read-only on Windows; use the platform callback.
        import os, shutil, stat
        def writable_then_remove(func, path, exc):
            os.chmod(path, stat.S_IWRITE)
            func(path)
        shutil.rmtree(self.root, onerror=writable_then_remove)
        self.tmp.cleanup()

    def run_plan(self, apply=False):
        with contextlib.redirect_stdout(io.StringIO()):
            return patches.run(self.root, self.plan, apply)

    def test_check_does_not_create_commits(self):
        before = [git(self.root/g['path'], 'rev-parse', 'HEAD') for g in self.plan]
        self.assertEqual(self.run_plan(), (0, 0, 4))
        self.assertEqual(before, [git(self.root/g['path'], 'rev-parse', 'HEAD') for g in self.plan])

    def test_apply_is_ordered_and_rerun_is_idempotent(self):
        self.assertEqual(self.run_plan(True), (4, 0, 0))
        self.assertEqual(self.run_plan(True), (0, 4, 0))
        for group in self.plan:
            repo = self.root/group['path']
            self.assertEqual((repo/'feature.txt').read_text(), 'feature 2\n')
            self.assertEqual(git(repo, 'status', '--porcelain'), '')
            for sha in group['commits']:
                self.assertIn(sha, git(repo, 'log', '--format=%B'))

    def test_existing_cherry_pick_with_different_hash_is_skipped(self):
        group = self.plan[0]
        repo = self.root/group['path']
        git(repo, 'cherry-pick', '-x', group['commits'][0])
        self.assertNotEqual(git(repo, 'rev-parse', 'HEAD'), group['commits'][0])
        self.assertEqual(self.run_plan(True), (3, 1, 0))

    def test_dirty_second_project_blocks_every_project(self):
        before = git(self.root/'media', 'rev-parse', 'HEAD')
        (self.root/'display/feature.txt').write_text('local edits\n')
        with self.assertRaisesRegex(patches.PatchError, 'Local changes'):
            self.run_plan(True)
        self.assertEqual(before, git(self.root/'media', 'rev-parse', 'HEAD'))

    def test_missing_source_commit_blocks_before_any_application(self):
        self.plan[1]['commits'][-1] = '0'*40
        before = git(self.root/'media', 'rev-parse', 'HEAD')
        with self.assertRaises(patches.PatchError):
            self.run_plan(True)
        self.assertEqual(before, git(self.root/'media', 'rev-parse', 'HEAD'))

    def test_conflict_stops_and_preserves_git_recovery_state(self):
        repo = self.root/'media'
        (repo/'feature.txt').write_text('conflicting local history\n')
        git(repo, 'commit', '-am', 'local history')
        before = git(self.root/'display', 'rev-parse', 'HEAD')
        with self.assertRaisesRegex(patches.PatchError, 'No automatic rollback'):
            self.run_plan(True)
        self.assertEqual(git(repo, 'rev-parse', 'CHERRY_PICK_HEAD'), self.plan[0]['commits'][0])
        self.assertEqual(before, git(self.root/'display', 'rev-parse', 'HEAD'))
        with self.assertRaisesRegex(patches.PatchError, 'Unfinished Git operation'):
            self.run_plan(True)
        git(repo, 'cherry-pick', '--abort')

    def test_requires_android_root(self):
        (self.root/'.repo').rmdir()
        with self.assertRaisesRegex(patches.PatchError, 'Android source root'):
            self.run_plan(True)


if __name__ == '__main__':
    unittest.main(verbosity=2)

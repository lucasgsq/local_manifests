import importlib.util
from pathlib import Path
import subprocess
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('sync', HERE.parent / 'concluir-sync-quark.py')
sync = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sync)


class MissingCheckoutTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix='case-', dir=str(HERE))).resolve()
        self.relative = 'packages/apps/Settings'
        self.output = self.root / 'backups/Settings'

    def command(self, *args):
        return subprocess.check_output(['git', *args], stderr=subprocess.PIPE).decode().strip()

    def seed(self, path):
        path.mkdir(parents=True)
        self.command('-C', str(path), 'init', '-q')
        self.command('-C', str(path), 'config', 'user.name', 'Quark tests')
        self.command('-C', str(path), 'config', 'user.email', 'test@example.invalid')
        (path / 'source.txt').write_text('source')
        self.command('-C', str(path), 'add', 'source.txt')
        self.command('-C', str(path), '-c', 'commit.gpgsign=false', 'commit', '-qm', 'baseline')
        return self.command('-C', str(path), 'rev-parse', 'HEAD')

    def test_fresh_missing_project_needs_no_worktree_or_metadata(self):
        result = sync.backup_project(self.root, self.relative, self.output)
        self.assertTrue(result['working_tree_missing'])
        self.assertTrue(result['git_metadata_missing'])
        self.assertFalse((self.root / self.relative).exists())

    def test_missing_checkout_keeps_metadata_history_even_with_missing_core_worktree(self):
        source = self.root / 'seed'
        head = self.seed(source)
        metadata = self.root / '.repo/projects/packages/apps/Settings.git'
        metadata.parent.mkdir(parents=True)
        self.command('clone', '--bare', str(source), str(metadata))
        self.command('--git-dir='+str(metadata), 'config', 'core.worktree', str(self.root/self.relative))
        result = sync.backup_project(self.root, self.relative, self.output)
        self.assertEqual(result['head'], head)
        self.assertTrue(Path(result['bundle']).is_file())
        self.assertIn(head, self.command('bundle', 'list-heads', result['bundle']))
        self.assertTrue((self.output / 'git-config').exists())

    def test_empty_metadata_is_recorded_without_invalid_empty_bundle(self):
        metadata = self.root / '.repo/projects/packages/apps/Settings.git'
        metadata.parent.mkdir(parents=True)
        self.command('init', '--bare', '-q', str(metadata))
        result = sync.backup_project(self.root, self.relative, self.output)
        self.assertIsNone(result['head'])
        self.assertIsNone(result['bundle'])
        self.assertFalse(result['git_metadata_missing'])

    def test_existing_dirty_worktree_is_still_rejected(self):
        repo = self.root / self.relative
        self.seed(repo)
        (repo / 'source.txt').write_text('local change')
        with self.assertRaises(RuntimeError):
            sync.backup_project(self.root, self.relative, self.output)
        self.assertEqual((repo / 'source.txt').read_text(), 'local change')

    def test_existing_clean_worktree_preserves_history_and_untracked_files(self):
        repo = self.root / self.relative
        head = self.seed(repo)
        (repo / 'private.txt').write_text('private fixture')
        result = sync.backup_project(self.root, self.relative, self.output)
        self.assertEqual(result['head'], head)
        self.assertEqual((self.output / 'untracked/private.txt').read_text(), 'private fixture')
        self.assertTrue(Path(result['bundle']).exists())

    def test_metadata_error_parser_remains_narrowly_scoped(self):
        self.assertEqual(sync.metadata_project(
            'hooks is different; repo sync --force-sync packages/apps/Settings'), self.relative)
        self.assertIsNone(sync.metadata_project(
            'hooks is different; repo sync --force-sync kernel/motorola/apq8084'))


if __name__ == '__main__':
    unittest.main(verbosity=2)

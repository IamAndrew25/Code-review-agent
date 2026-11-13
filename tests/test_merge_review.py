import importlib.util
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from static_analysis import run_bandit
from git_scope import changed_files
from test_features import git


class MergeReviewTests(unittest.TestCase):
    @unittest.skipUnless(importlib.util.find_spec('bandit'), 'Bandit not installed')
    def test_bandit_cannot_be_shadowed_by_reviewed_project(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'app.py').write_text('def run(value):\n    return eval(value)\n')
            (root / 'bandit.py').write_text(
                'from pathlib import Path\nPath("executed").write_text("test")\n'
                'print(\'{"results": [], "errors": []}\')\n')
            previous = Path.cwd()
            try:
                os.chdir(root)
                with patch.dict(os.environ, {'PYTHONPATH': str(root)}):
                    report = run_bandit(root, ['app.py'])
            finally:
                os.chdir(previous)
            self.assertFalse((root / 'executed').exists())
            self.assertEqual(report['status'], 'complete')
            self.assertTrue(any(f['rule'] == 'B307' for f in report['findings']))

    def test_dangling_symlink_is_not_reported_as_deleted(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            git(tmp, 'init')
            (root / 'a.py').write_text('x = 1\n')
            git(tmp, 'add', '.')
            git(tmp, '-c', 'user.name=Test', '-c', 'user.email=test@example.invalid', 'commit', '-m', 'baseline')
            (root / 'link.py').symlink_to(root / 'missing.py')
            selected, deleted, _ = changed_files(root)
            self.assertIn('link.py', selected)
            self.assertNotIn('link.py', deleted)

import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import sys
import unittest

from agent import review
from git_scope import changed_files
from project_context import build_graph, related_context
from reporting import render_markdown
from static_analysis import run_bandit
from test_agent import FakeClient, empty


def git(root, *args):
    return subprocess.run(['git', '-C', str(root), *args], check=True, capture_output=True)


class FeatureTests(unittest.TestCase):
    def test_context_follows_imports_and_callers(self):
        sources = {'pkg/routes.py': 'from .service import lookup\nlookup(user)',
                   'pkg/service.py': 'def lookup(user):\n    return user', 'other.py': 'unrelated = True'}
        graph = build_graph(sources)
        text, info = related_context('pkg/service.py', sources, graph)
        self.assertIn('pkg/routes.py', info['files'])
        self.assertIn('lookup(user)', text)
        self.assertNotIn('other.py', info['files'])
        _, limited = related_context('pkg/service.py', sources, graph, limit=5)
        self.assertIn('pkg/routes.py', limited['truncated'])

    def test_context_reaches_actual_model_request(self):
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, 'caller.py').write_text('from service import lookup\nlookup(user)')
            Path(tmp, 'service.py').write_text('def lookup(user):\n    return user')
            prompts = []
            def handler(prompt):
                prompts.append(prompt)
                return empty(prompt)
            result = review(FakeClient(handler), tmp)
            self.assertEqual(result['status'], 'complete')
            service_prompt = next(p for p in prompts if p.startswith('PRIMARY FILE: service.py'))
            self.assertIn('CONTEXT FILE: caller.py', service_prompt)

    def test_git_scope_staged_unstaged_untracked_and_deleted(self):
        with tempfile.TemporaryDirectory() as tmp:
            git(tmp, 'init')
            for name in ['a.py', 'b.py', 'gone.py', 'unchanged.py']:
                Path(tmp, name).write_text('x = 1\n')
            git(tmp, 'add', '.')
            git(tmp, '-c', 'user.name=Test', '-c', 'user.email=test@example.invalid', 'commit', '-m', 'baseline')
            Path(tmp, 'a.py').write_text('x = 2\n')
            git(tmp, 'add', 'a.py')
            Path(tmp, 'b.py').write_text('x = 3\n')
            Path(tmp, 'new file.py').write_text('x = 4\n')
            Path(tmp, 'gone.py').unlink()
            selected, deleted, _ = changed_files(tmp)
            self.assertEqual(selected, ['a.py', 'b.py', 'new file.py'])
            self.assertEqual(deleted, ['gone.py'])
            result = review(FakeClient(empty), tmp, changed=True)
            self.assertEqual([c['file'] for c in result['coverage']], selected)
            self.assertEqual(result['scope']['deleted'], deleted)
            self.assertEqual(result['status'], 'complete')
            with self.assertRaises(ValueError):
                changed_files(tmp, 'not-a-ref')

    def test_secrets_and_generated_directories_are_excluded(self):
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, '.env').write_text('SECRET=private')
            Path(tmp, 'node_modules').mkdir()
            Path(tmp, 'node_modules/bad.py').write_text('eval(user)')
            Path(tmp, 'app.py').write_text('x = 1')
            result = review(FakeClient(empty), tmp)
            self.assertEqual([c['file'] for c in result['coverage']], ['app.py'])
            self.assertIn('.env', result['excluded'])

    def test_report_escapes_untrusted_text_and_shows_incomplete(self):
        report = dict(status='incomplete', model_calls=1, coverage=[], skipped=[], findings=[
            dict(file='a.py', line=1, severity='high', snippet='<script>evil()</script>',
                 problem='[click](https://example.invalid)', risk='x', fix='y')])
        text = render_markdown(report)
        self.assertIn('**incomplete**', text)
        self.assertNotIn('<script>', text)
        self.assertIn('&lt;script&gt;', text)
        self.assertNotIn('[click]', text)

    @unittest.skipUnless(importlib.util.find_spec('bandit'), 'Bandit not installed')
    def test_real_bandit_finding_and_syntax_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, 'bad.py').write_text('def run(value):\n    return eval(value)\n')
            static = run_bandit(tmp, ['bad.py'])
            self.assertEqual(static['status'], 'complete')
            self.assertTrue(any(f['rule'] == 'B307' and f['line'] == 2 for f in static['findings']))
            Path(tmp, 'broken.py').write_text('def broken(:')
            self.assertEqual(run_bandit(tmp, ['broken.py'])['status'], 'incomplete')


class OutputTests(unittest.TestCase):
    def test_markdown_cli_file_and_exit_status(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp, 'project')
            root.mkdir()
            Path(root, 'app.py').write_text('x = 1')
            output = Path(tmp, 'report.md')
            proc = subprocess.run([sys.executable, 'agent.py', str(root), '--max-steps', '0',
                                   '--format', 'markdown', '--output', str(output)], capture_output=True, text=True)
            self.assertEqual(proc.returncode, 3)
            self.assertEqual(proc.stdout, '')
            self.assertIn('**incomplete**', output.read_text())

import json
import tempfile
import unittest
from pathlib import Path
from agent import review, validate_findings
from test_agent import FakeClient, empty

class EdgeTests(unittest.TestCase):
    def test_missing_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                review(FakeClient(empty), Path(tmp) / 'missing')

    def test_empty_file_needs_no_model(self):
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, 'empty.py').touch()
            result = review(FakeClient(empty), tmp, max_steps=0)
            self.assertEqual(result['status'], 'complete')
            self.assertEqual(result['model_calls'], 0)

    def test_nested_files_and_zero_budget(self):
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, 'nested').mkdir()
            Path(tmp, 'a.py').write_text('x=1')
            Path(tmp, 'nested/b.py').write_text('x=2')
            result = review(FakeClient(empty), tmp, max_steps=0)
            self.assertEqual(len(result['coverage']), 2)
            self.assertTrue(all(x['status'] == 'incomplete' for x in result['coverage']))

    def test_server_failure(self):
        def fail(_):
            raise ConnectionError('offline')
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, 'a.py').write_text('x=1')
            result = review(FakeClient(fail), tmp)
            self.assertEqual(result['status'], 'incomplete')
            self.assertIn('ConnectionError', result['coverage'][0]['reason'])

    def test_fenced_json(self):
        self.assertEqual(validate_findings('```json\n{"findings": []}\n```', 'x', '', 0, 0), ([], 0))

    def test_evidence_must_be_in_supplied_chunk(self):
        item = dict(line=1, snippet='SECRET', problem='x', risk='x', fix='x')
        self.assertEqual(validate_findings(json.dumps({'findings':[item]}), 'x', 'abcSECRET', 0, 3), ([], 1))

    def test_unicode_line_separator(self):
        item = dict(line=2, snippet='target', problem='x', risk='x', fix='x')
        content = 'a\u2028b\ntarget'
        valid, rejected = validate_findings(json.dumps({'findings':[item]}), 'x', content, 0, len(content))
        self.assertEqual(len(valid), 1)
        self.assertEqual(rejected, 0)

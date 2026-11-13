import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from agent import review
from tools import CHUNK_SIZE, read_file, _safe_path


class FakeClient:
    def __init__(self, handler):
        self.chat = SimpleNamespace(completions=self)
        self.handler = handler
    def create(self, **kwargs):
        result = self.handler(kwargs['messages'][-1]['content'])
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=result))])


def empty(_):
    return '{"findings": []}'


class ReviewTests(unittest.TestCase):
    def test_chunks_reconstruct_long_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            content = 'á' * (CHUNK_SIZE + 10) + '\nend'
            Path(tmp, 'long.py').write_text(content)
            first = read_file('long.py', root=tmp)
            second = read_file('long.py', first['next_offset'], root=tmp)
            self.assertEqual(first['content'] + second['content'], content)
            self.assertIsNone(second['next_offset'])
            with self.assertRaises(ValueError):
                _safe_path('../outside', tmp)

    def test_long_file_is_reviewed_to_end_and_evidence_checked(self):
        with tempfile.TemporaryDirectory() as tmp:
            content = '# padding\n' * 600 + 'PASSWORD = "secret"\n'
            Path(tmp, 'app.py').write_text(content)
            def model(prompt):
                if 'PASSWORD = "secret"' in prompt:
                    return json.dumps({'findings': [{'line': 601, 'snippet': 'PASSWORD = "secret"', 'problem': 'Hardcoded secret', 'risk': 'Exposure', 'fix': 'Use environment variables'}]})
                return empty(prompt)
            result = review(FakeClient(model), tmp)
            self.assertEqual(result['status'], 'complete')
            self.assertEqual(result['findings'][0]['line'], 601)
            self.assertEqual(result['model_calls'], 2)

    def test_limit_and_bad_response_mark_incomplete(self):
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, 'a.py').write_text('a' * (CHUNK_SIZE + 1))
            limited = review(FakeClient(empty), tmp, max_steps=1)
            self.assertEqual(limited['status'], 'incomplete')
            self.assertEqual(limited['coverage'][0]['characters_processed'], CHUNK_SIZE)
            bad = review(FakeClient(lambda _: 'invalid json'), tmp)
            self.assertEqual(bad['status'], 'incomplete')
            self.assertIn('JSONDecodeError', bad['coverage'][0]['reason'])

    def test_invalid_evidence_is_not_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, 'a.py').write_text('safe = True\n')
            fake = {'findings': [{'line': 1, 'snippet': 'invented', 'problem': 'x', 'risk': 'x', 'fix': 'x'}]}
            result = review(FakeClient(lambda _: json.dumps(fake)), tmp)
            self.assertEqual(result['findings'], [])
            self.assertEqual(result['status'], 'incomplete')

    def test_unreadable_and_symlink_are_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, 'binary').write_bytes(b'\xff')
            Path(tmp, 'link').symlink_to('/tmp')
            result = review(FakeClient(empty), tmp)
            self.assertEqual(result['status'], 'incomplete')
            self.assertEqual(result['coverage'][0]['status'], 'unreadable')
            self.assertTrue(result['skipped'])


if __name__ == '__main__':
    unittest.main()

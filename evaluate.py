"""Repeatable live smoke evaluation. Findings are saved for manual classification."""
import json
import tempfile
from pathlib import Path
from agent import review


def main():
    results = []
    base = Path(__file__).parent / 'tests/fixtures'
    for repeat in range(3):
        for case in ('vulnerable', 'safe'):
            result = review(root=base / case)
            results.append({'case': case, 'repeat': repeat + 1, 'result': result})
            print(case, repeat + 1, result['status'], len(result['findings']), flush=True)
    with tempfile.TemporaryDirectory() as tmp:
        Path(tmp, 'long.py').write_text('# padding\n' * 600 + 'import subprocess\ndef run(user_input):\n    subprocess.run(user_input, shell=True)\n')
        result = review(root=tmp)
        results.append({'case': 'long_command_injection', 'result': result})
        print('long_command_injection', result['status'], len(result['findings']), flush=True)
    Path('evaluation-results.json').write_text(json.dumps(results, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()

"""Live CLI evaluation of multi-file projects, static analysis, reports, and Git scope."""
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

from reporting import render_markdown


def main():
    records = []
    def run(name, root, *options):
        command = [sys.executable, 'agent.py', str(root), '--bandit', '--max-steps', '20', *options]
        proc = subprocess.run(command, capture_output=True, text=True, timeout=300)
        if not proc.stdout.strip():
            raise RuntimeError(proc.stderr)
        result = json.loads(proc.stdout)
        records.append({'case': name, 'exit_code': proc.returncode, 'result': result})
        print(name, 'exit', proc.returncode, 'AI findings', len(result['findings']), 'Bandit findings', len(result['static_analysis']['findings']), flush=True)
        return result
    unsafe = run('multi_file_unsafe', 'tests/projects/unsafe_shop')
    safe = run('multi_file_safe', 'tests/projects/safe_shop')
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp, 'shop')
        shutil.copytree('tests/projects/safe_shop', root)
        def git(*args):
            subprocess.run(['git', '-C', str(root), *args], check=True, capture_output=True)
        git('init')
        git('add', '.')
        git('-c', 'user.name=Test', '-c', 'user.email=test@example.invalid', 'commit', '-m', 'safe baseline')
        (root / 'queries.py').write_text('def user_query(name):\n    return f"SELECT id, name FROM users WHERE name = \'{name}\'", ()\n')
        changed = run('changed_file_with_context', root, '--changed')
    checks = {
        'all_complete': all(r['exit_code'] == 0 and r['result']['status'] == 'complete' for r in records),
        'unsafe_sql_detected': any(f['file'] == 'queries.py' and f['line'] == 2 for f in unsafe['findings']),
        'safe_no_ai_findings': not safe['findings'],
        'safe_no_static_findings': not safe['static_analysis']['findings'],
        'bandit_sql_detected': any(f['rule'] == 'B608' for f in unsafe['static_analysis']['findings']),
        'changed_only_one_target': [c['file'] for c in changed['coverage']] == ['queries.py'],
        'changed_context_present': 'routes.py' in changed['coverage'][0]['context']['files'],
        'changed_sql_detected': any(f['file'] == 'queries.py' and f['line'] == 2 for f in changed['findings']),
    }
    Path('project-evaluation-results.json').write_text(json.dumps({'checks': checks, 'runs': records}, ensure_ascii=False, indent=2))
    Path('example-report.md').write_text(render_markdown(unsafe))
    for name, ok in checks.items():
        print(name, 'PASS' if ok else 'FAIL', flush=True)
    raise SystemExit(0 if all(checks.values()) else 1)


if __name__ == '__main__':
    main()

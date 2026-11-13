"""Run the actual CLI, including live model calls; preserve stdout and exit codes."""
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile


def main():
    results = []
    def run(name, args, expected_code, expected_status=None, expected_lines=None, env=None):
        proc = subprocess.run([sys.executable, 'agent.py', *args], capture_output=True, text=True,
                              timeout=120, env=env)
        parsed = json.loads(proc.stdout) if proc.stdout.strip() else None
        passed = proc.returncode == expected_code
        if expected_status:
            passed = passed and parsed is not None and parsed['status'] == expected_status
        if expected_lines is not None:
            passed = passed and parsed is not None and sorted(f['line'] for f in parsed['findings']) == expected_lines
        results.append(dict(case=name, passed=passed, exit_code=proc.returncode,
                            output=parsed, stderr=proc.stderr))
        print(name, 'PASS' if passed else 'FAIL', 'exit=', proc.returncode, flush=True)
    live_env = {**os.environ, 'OPENAI_BASE_URL': 'http://localhost:8080/v1',
                'OPENAI_API_KEY': 'not-needed', 'MODEL': 'mlx-community/Qwen3.6-35B-A3B-4bit'}
    run('live_vulnerable', ['tests/fixtures/vulnerable'], 0, 'complete', [3, 7], live_env)
    run('live_safe', ['tests/fixtures/safe'], 0, 'complete', [], live_env)
    run('exhausted_budget', ['tests/fixtures/safe', '--max-steps', '0'], 3, 'incomplete', [], live_env)
    run('negative_budget', ['tests/fixtures/safe', '--max-steps', '-1'], 2, env=live_env)
    with tempfile.TemporaryDirectory() as tmp:
        run('missing_project', [str(Path(tmp)/'absent')], 2, env=live_env)
        run('empty_project', [tmp], 0, 'complete', [], live_env)
        Path(tmp, 'binary.dat').write_bytes(b'\xff\x00')
        run('binary_file', [tmp], 3, 'incomplete', [], live_env)
    # Reserve a non-listening local port to simulate an unavailable model server.
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        env = {**live_env, 'OPENAI_BASE_URL': f'http://127.0.0.1:{sock.getsockname()[1]}/v1'}
        run('server_offline', ['tests/fixtures/safe'], 3, 'incomplete', [], env)
    Path('cli-results.json').write_text(json.dumps(results, ensure_ascii=False, indent=2))
    raise SystemExit(0 if all(r['passed'] for r in results) else 1)


if __name__ == '__main__':
    main()

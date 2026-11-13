"""Run installed Bandit against explicit Python targets, without executing the target."""
import json
from pathlib import Path
import subprocess
import sys


def run_bandit(root, paths, timeout=60):
    findings, errors, scanned = [], [], []
    for path in paths:
        if not path.endswith('.py'):
            continue
        target = Path(root, path).resolve()
        try:
            proc = subprocess.run([sys.executable, '-I', '-m', 'bandit', '-f', 'json', '-q', '--ignore-nosec', str(target)],
                                  capture_output=True, text=True, timeout=timeout)
            if proc.returncode not in (0, 1):
                raise ValueError(proc.stderr.strip() or 'Bandit failed')
            data = json.loads(proc.stdout)
            errors.extend({'file': path, 'reason': item.get('reason', str(item))} for item in data.get('errors', []))
            if data.get('errors'):
                continue
            scanned.append(path)
            for item in data.get('results', []):
                findings.append({'file': path, 'line': item['line_number'], 'rule': item['test_id'],
                                 'severity': item['issue_severity'].lower(), 'confidence': item['issue_confidence'].lower(),
                                 'problem': item['issue_text'], 'snippet': item['code'],
                                 'reference': item.get('more_info', '')})
        except (OSError, ValueError, subprocess.TimeoutExpired) as error:
            errors.append({'file': path, 'reason': str(error)})
    return {'status': 'incomplete' if errors else 'complete', 'findings': findings,
            'errors': errors, 'files': scanned, 'engine': 'bandit'}

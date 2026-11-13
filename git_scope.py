"""Select current working-tree files changed relative to a Git commit."""
from pathlib import Path
import os
import subprocess


def git(root, *args):
    result = subprocess.run(['git', '-C', str(root), *args], capture_output=True, timeout=30)
    if result.returncode:
        raise ValueError(result.stderr.decode(errors='replace').strip() or 'Git command failed')
    return result.stdout


def changed_files(root, base='HEAD'):
    root = Path(root).resolve()
    top = Path(git(root, 'rev-parse', '--show-toplevel').decode().strip()).resolve()
    if root != top:
        raise ValueError('--changed requires the repository root as the project path')
    commit = git(root, 'rev-parse', '--verify', '--end-of-options', base + '^{commit}').decode().strip()
    changed = git(root, 'diff', '--name-only', '-z', '--no-renames', commit, '--')
    untracked = git(root, 'ls-files', '--others', '--exclude-standard', '-z')
    names = sorted({p.decode('utf-8', errors='surrogateescape') for p in (changed + untracked).split(b'\0') if p})
    deleted = [name for name in names if not os.path.lexists(root / name)]
    return [name for name in names if name not in deleted], deleted, commit

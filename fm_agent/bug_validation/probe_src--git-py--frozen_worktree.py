"""Probe script for bug: frozen_worktree — git add -A respects .gitignore,
so untracked gitignored files are not captured in the snapshot.

Spec claim: "The snapshot commit captures ... all untracked files"
Actual: git add -A silently skips gitignored paths.
Trigger: gitignored untracked file present in proj_dir.
"""

import sys
import os
import tempfile
import subprocess
import shutil

# Ensure the repo root is on sys.path so that `src.git` is importable
_repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

try:
    from src.git import frozen_worktree
except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)

# Step 1: Create a temporary git repo
repo_dir = tempfile.mkdtemp(prefix='fm_probe_repo_')
try:
    subprocess.run(['git', 'init', repo_dir], check=True, capture_output=True)

    # Step 2: Create .gitignore that ignores *.log
    with open(os.path.join(repo_dir, '.gitignore'), 'w') as f:
        f.write('*.log\n')

    # Step 3: Create a tracked file (so we have at least one commit)
    with open(os.path.join(repo_dir, 'main.py'), 'w') as f:
        f.write('print("hello")\n')

    subprocess.run(['git', '-C', repo_dir, 'add', '.'], check=True, capture_output=True)
    subprocess.run(
        ['git', '-C', repo_dir, 'commit', '-m', 'initial', '--quiet'],
        check=True, capture_output=True,
    )

    # Step 4: Create an untracked gitignored file (data.log)
    with open(os.path.join(repo_dir, 'data.log'), 'w') as f:
        f.write('should be in snapshot per spec, but .gitignore excludes it\n')

    # Step 5: Create an untracked non-gitignored file (should always be in snapshot)
    with open(os.path.join(repo_dir, 'important.txt'), 'w') as f:
        f.write('this should always be in the snapshot\n')

    # Step 6: Call frozen_worktree
    try:
        with frozen_worktree(repo_dir) as wt:
            # PER SPEC: data.log (untracked) should be in snapshot
            # ACTUAL BUG: git add -A respects .gitignore, so data.log is missing
            data_log_present = os.path.exists(os.path.join(wt, 'data.log'))
            important_present = os.path.exists(os.path.join(wt, 'important.txt'))
            main_present = os.path.exists(os.path.join(wt, 'main.py'))
            gitignore_present = os.path.exists(os.path.join(wt, '.gitignore'))

            # The non-gitignored untracked file should ALWAYS be there
            # (this is our sanity check that the snapshot captured untracked files)
            if not important_present:
                print('ERROR: non-gitignored untracked file important.txt is missing from snapshot')
                sys.exit(1)

            # The bug: data.log is gitignored and untracked, so git add -A skips it
            # Spec says "all untracked files" — data.log should be present
            if not data_log_present:
                print(f'CONFIRMED — data.log (gitignored untracked file) missing from snapshot '
                      f'(important.txt present={important_present}, '
                      f'data.log present={data_log_present}, '
                      f'main.py present={main_present}, '
                      f'.gitignore present={gitignore_present})')
            else:
                print(f'NOT CONFIRMED — data.log was unexpectedly present in snapshot '
                      f'(important.txt present={important_present}, '
                      f'data.log present={data_log_present})')

    finally:
        # Clean up the worktree
        if os.path.exists(wt):
            try:
                subprocess.run(
                    ['git', '-C', repo_dir, 'worktree', 'remove', '--force', wt],
                    capture_output=True,
                )
            except Exception:
                pass

finally:
    # Clean up the temp repo
    shutil.rmtree(repo_dir, ignore_errors=True)

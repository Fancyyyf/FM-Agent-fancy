# Bug Report: frozen_worktree

**Source file:** `/tmp/fm_agent_wt_FM-Agent_dlsr6ukl/snapshot/fm_agent/extracted_functions/src/git-py/frozen_worktree.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- A new, unique temporary directory is created under the system tempdir. Its name
    begins with "fm_agent_wt_" followed by the basename of proj_dir.
  - When proj_dir is a git repository with a reachable HEAD commit:
      - A private git index (GIT_INDEX_FILE) is used so that proj_dir's real index
        and working tree are never modified.
      - The snapshot commit captures the full state of proj_dir at entry time:
        HEAD tree + all tracked modifications + all untracked files, with every
        path in exclude removed from the snapshot commit tree.
      - That commit becomes a detached git worktree checked out inside the tempdir
        at a "snapshot" subdirectory. The yielded path is this snapshot subdirectory.
      - If copy_excluded is truthy: for each name in exclude, if the corresponding
        subdirectory exists in proj_dir and does not already exist at the same
        relative path in the snapshot worktree, that subdirectory is recursively
        copied (with symlinks preserved) into the snapshot worktree.
  - When proj_dir is NOT a git repository or has no reachable HEAD:
      - A plain recursive directory copy is performed from proj_dir into the
        snapshot subdirectory, using copytree with each name in exclude passed as
        an ignore pattern and with symlinks preserved. The yielded path is the
        snapshot subdirectory.
      - If copy_excluded is truthy: excluded subdirectories are copied into the
        snapshot worktree under the same conditions as the git-path case.
  - The absolute path of the snapshot worktree is printed to stdout along with
    platform-appropriate removal instructions referencing either "git worktree
    remove" (git path) or "rm -rf" (non-git path).
  - The snapshot worktree and its parent temporary directory persist after the
    context manager exits; automatic cleanup is not performed.
  - If any git or filesystem operation fails (e.g. git command returns non-zero,
    directory is not writable), the corresponding subprocess.CalledProcessError or
    OSError propagates to the caller.

---

### Actual Behavior

If the generator body executed without raising an exception (i.e., after the generator has been advanced to its single yield and then exhausted naturally), the following holds:

1. The generator yields exactly one value  a string wt  which is the absolute, normalized path of a newly created snapshot directory.
2. wt exists and is a directory in a temporary location (its parent is the base directory returned by tempfile.mkdtemp).
3. The original proj_dir is completely unchanged: its working tree, index, HEAD, and all refs are exactly as they were before the function was called.
4. Two cases depending on the git state of proj_dir:
   a. Git case (is_git = True):
      - A new detached worktree was added to proj_dir's git repository, linked to wt, using a temporary index file located in the base directory.
      - The snapshot at wt represents the state of HEAD plus all uncommitted edits and untracked files that were not gitignored, except that the subdirectories named in `exclude` were explicitly removed from the commit tree (so they are absent from the committed contents unless they were never tracked).
      - If copy_excluded is True, then for every name in `exclude` where os.path.isdir(proj_dir/name) evaluated to True at entry time, wt/name now exists as a directory and contains a recursive copy (symlinks preserved) of proj_dir/name.
   b. Nongit case (is_git = False):
      - wt was created by shutil.copytree(proj_dir, wt, ignore=shutil.ignore_patterns(*exclude), symlinks=True). It therefore contains every file and directory from proj_dir except those whose names match any of the exclude patterns.
      - If copy_excluded is True, then for every name in `exclude` where os.path.isdir(proj_dir/name) was true, wt/name is a recursive copy (symlinks preserved) of proj_dir/name.
5. Stdout has received the two messages: "[Pipeline] Snapshot created at: <wt>" and a hint about how to remove the snapshot (using `git worktree remove` when is_git, or `rm -rf` otherwise).
6. The generator context manager has exited (i.e., the with-block body has completed). The snapshot directory and its parent base directory are NOT cleaned up.

---

## Code Evidence

Line 45

---

## Trigger Condition

Specification B requires that the snapshot capture 'all untracked files'. The code runs `git add -A`, which respects .gitignore and skips 'data.log'. Consequently, the snapshot does not contain the untracked gitignored file, violating the specification.

---

## How to trigger the bug

Create a git repository with a `.gitignore` that matches a specific file pattern (e.g., `*.log`). Create an untracked file matching that pattern (e.g., `data.log`). Call `frozen_worktree()` on the repository. The gitignored untracked file will be absent from the snapshot, even though the specification requires "all untracked files" to be captured.

### Inputs

| Parameter | Value |
|-----------|-------|
| proj_dir | A temporary git repository with a `.gitignore` containing `*.log` |
| exclude | `("fm_agent",)` (default) |
| copy_excluded | `True` (default) |

### Expected (spec-correct) Output

`data.log` (the gitignored untracked file) should be present in the snapshot directory, alongside the non-gitignored untracked file `important.txt` and the tracked file `main.py`.

### Actual (buggy) Output

`data.log` is **absent** from the snapshot directory. `important.txt` (non-gitignored untracked) is present, `main.py` (tracked) is present. The `git add -A` command silently skipped `data.log` because it matches the `.gitignore` pattern.

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import os, sys, tempfile, subprocess, shutil
sys.path.insert(0, '/tmp/fm_agent_wt_FM-Agent_dlsr6ukl/snapshot')
from src.git import frozen_worktree

# Create a temp git repo with .gitignore ignoring *.log
repo_dir = tempfile.mkdtemp()
subprocess.run(['git', 'init', repo_dir], check=True, capture_output=True)
with open(os.path.join(repo_dir, '.gitignore'), 'w') as f:
    f.write('*.log\n')
with open(os.path.join(repo_dir, 'main.py'), 'w') as f:
    f.write('print("hello")\n')
subprocess.run(['git', '-C', repo_dir, 'add', '.'], check=True, capture_output=True)
subprocess.run(['git', '-C', repo_dir, 'commit', '-m', 'init', '--quiet'], check=True, capture_output=True)

# Create untracked gitignored file
with open(os.path.join(repo_dir, 'data.log'), 'w') as f:
    f.write('should be in snapshot')

with frozen_worktree(repo_dir) as wt:
    print('data.log in snapshot:', os.path.exists(os.path.join(wt, 'data.log')))
    # actual (buggy) output: False
    # expected (correct) output: True
```

---

## Probe Script

```python
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
```

### Probe Output

```
[Pipeline] Snapshot created at: /tmp/fm_agent_wt_fm_probe_repo_w8884uto_tsrfxpfd/snapshot
[Pipeline] Snapshot is kept after the run. Remove with: git -C /tmp/fm_probe_repo_w8884uto worktree remove --force /tmp/fm_agent_wt_fm_probe_repo_w8884uto_tsrfxpfd/snapshot
CONFIRMED — data.log (gitignored untracked file) missing from snapshot (important.txt present=True, data.log present=False, main.py present=True, .gitignore present=True)
```

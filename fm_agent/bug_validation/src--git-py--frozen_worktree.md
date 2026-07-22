# Bug Report: frozen_worktree

**Source file:** `src/git.py`
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
  - If any git or filesystem operation fails (e.g. git ... (line truncated to 2000 chars)

---

### Actual Behavior

After the function body has executed up to and including the yield statement (suspending the generator), the following holds:

- A unique temporary directory base was created via tempfile.mkdtemp inside the system temporary directory; its absolute path is stored in variable `base`.
- The variable `wt` holds the absolute path `os.path.join(base, 'snapshot')`, which is a directory that now exists.

**If `proj_dir` is a git repository with at least one commit** (i.e., `git -C proj_dir rev-parse --verify HEAD` succeeded):
  * A private git index file was created at `os.path.join(base, 'index')`.
  * The HEAD tree was read into that index (`git read-tree HEAD`).
  * All workingtree changes (tracked edits and untracked files, respecting `.gitignore`) were staged via `git add -A`.
  * For every name in `exclude`, `git rm -r --cached --quiet --ignore-unmatch -- <name>` was executed, removing those entries from the private index if present.
  * A tree object was written from the index (`git write-tree`).
  * A new commit object was created with that tree, parent HEAD, and message `'fm_agent snapshot'` (`git commit-tree`).
  * A detached worktree was added at `wt` referencing that commit (`git worktree add --detach <wt> <snap>`).
  * `wt` is a valid git checkout containing the committed state plus uncommitted edits and untracked files, **excluding** any paths that are gitignored **or** whose names are listed in `exclude`.

**Otherwise** (`proj_dir` is not a git repo or has no commit):
  * `shutil.copytree(proj_dir, wt, ignore=shutil.ignore_patterns(*exclude), symlinks=True)` executed successfully.
  * `wt` is a plain directory copy of `proj_dir`, preserving symlinks, but omitting any files or subdirectories whose names match the patterns in `exclude`.
  * An INFOlevel log message was emitted stating that a copy was performed.

**If `copy_excluded` is True:**
  * For each name in `exclude`, if `os.path.join(proj_dir, name)` exists a... (line truncated to 2000 chars)

---

## Code Evidence

Line 45: _git("add", "-A", env=env)

---

## Trigger Condition

The code's use of `git add -A` skips files that match .gitignore patterns, so untracked gitignored files are not included in the snapshot. The specification requires capturing all untracked files without exception for .gitignore.

---

## How to trigger the bug

The bug is triggered when a git repository contains untracked files that match `.gitignore` patterns. The `git add -A` command used to stage files in the private index silently skips gitignored paths, so those files are never included in the snapshot commit. The specification explicitly states that the snapshot should capture "all untracked files" — with no carve-out for `.gitignore`-matched files.

### Inputs

| Parameter | Value |
|-----------|-------|
| `proj_dir` | A git repository with at least one commit, containing a `.gitignore` that matches `*.secret` and an untracked file `test.secret` |
| `exclude` | `()` (empty tuple — no additional exclusions) |
| `copy_excluded` | `False` |

### Expected (spec-correct) Output

The snapshot worktree at the yielded path should contain `test.secret` (the gitignored untracked file), alongside all other files.

### Actual (buggy) Output

The snapshot worktree does NOT contain `test.secret` — the file is missing because `git add -A` respects `.gitignore` and silently skipped it.

### How to Reproduce

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import os, subprocess, tempfile, shutil
import sys
sys.path.insert(0, ".")
from src.git import frozen_worktree

# Create a test git repo
tmp = tempfile.mkdtemp()
proj_dir = os.path.join(tmp, "repo")
os.makedirs(proj_dir)
subprocess.run(["git", "init"], cwd=proj_dir, check=True, capture_output=True, text=True)
subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=proj_dir, check=True, capture_output=True, text=True)
subprocess.run(["git", "config", "user.name", "Test"], cwd=proj_dir, check=True, capture_output=True, text=True)

# Create .gitignore that ignores *.secret
with open(os.path.join(proj_dir, ".gitignore"), "w") as f:
    f.write("*.secret\n")
with open(os.path.join(proj_dir, "tracked.txt"), "w") as f:
    f.write("hello\n")
subprocess.run(["git", "add", ".gitignore", "tracked.txt"], cwd=proj_dir, check=True, capture_output=True, text=True)
subprocess.run(["git", "commit", "-m", "init"], cwd=proj_dir, check=True, capture_output=True, text=True)

# Create a gitignored untracked file
with open(os.path.join(proj_dir, "test.secret"), "w") as f:
    f.write("secret\n")

# Trigger the bug
with frozen_worktree(proj_dir, exclude=(), copy_excluded=False) as wt:
    # actual (buggy) output: test.secret is NOT present
    print("test.secret present:", os.path.isfile(os.path.join(wt, "test.secret")))
    # expected (correct) output: True
```

---

## Probe Script

```python
"""Probe script for bug: src--git-py--frozen_worktree

Bug: git add -A skips gitignored untracked files, so they are omitted from the
snapshot worktree. The spec requires capturing ALL untracked files.
"""

import os
import subprocess
import shutil
import tempfile
import sys

# The probe is at fm_agent/bug_validation/probe_*.py, three levels deep.
# Go up three levels to reach the repo root.
_repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _repo_root)

try:
    from src.git import frozen_worktree
except Exception as e:
    print(f"ERROR: Failed to import frozen_worktree: {e}")
    sys.exit(1)


def main():
    # Create a temporary git repo outside the FM-Agent workspace
    tmp_root = tempfile.mkdtemp(prefix="bug_probe_")
    proj_dir = os.path.join(tmp_root, "testrepo")
    os.makedirs(proj_dir)

    try:
        # Initialize a git repo
        subprocess.run(["git", "init"], cwd=proj_dir, check=True,
                       capture_output=True, text=True)

        # Configure git user (required for commits)
        subprocess.run(["git", "config", "user.email", "test@test.com"],
                       cwd=proj_dir, check=True, capture_output=True, text=True)
        subprocess.run(["git", "config", "user.name", "Test"],
                       cwd=proj_dir, check=True, capture_output=True, text=True)

        # Create .gitignore that ignores *.secret files
        gitignore_path = os.path.join(proj_dir, ".gitignore")
        with open(gitignore_path, "w") as f:
            f.write("*.secret\n")

        # Create a tracked file
        tracked_path = os.path.join(proj_dir, "tracked.txt")
        with open(tracked_path, "w") as f:
            f.write("hello\n")

        # Stage and commit the tracked file + .gitignore
        subprocess.run(["git", "add", ".gitignore", "tracked.txt"],
                       cwd=proj_dir, check=True, capture_output=True, text=True)
        subprocess.run(["git", "commit", "-m", "initial"],
                       cwd=proj_dir, check=True, capture_output=True, text=True)

        # Create an untracked file that matches .gitignore
        secret_path = os.path.join(proj_dir, "test.secret")
        with open(secret_path, "w") as f:
            f.write("secret content\n")

        # Also create an untracked file that does NOT match .gitignore
        normal_path = os.path.join(proj_dir, "normal.txt")
        with open(normal_path, "w") as f:
            f.write("normal content\n")

        # Call frozen_worktree through the public entry point.
        # Use empty exclude and copy_excluded=False to keep the test simple.
        snapshot_dir = None
        with frozen_worktree(proj_dir, exclude=(), copy_excluded=False) as wt:
            snapshot_dir = wt

            # Check: does the gitignored untracked file exist in the snapshot?
            snapshot_secret = os.path.join(wt, "test.secret")
            secret_present = os.path.isfile(snapshot_secret)

            # Check: does the normal untracked file exist?
            snapshot_normal = os.path.join(wt, "normal.txt")
            normal_present = os.path.isfile(snapshot_normal)

            # Check: tracked file exists?
            snapshot_tracked = os.path.join(wt, "tracked.txt")
            tracked_present = os.path.isfile(snapshot_tracked)

        # The spec claims: "HEAD tree + all tracked modifications + all untracked files"
        # If the gitignored file is missing, the bug is CONFIRMED.
        expected = True    # spec says it SHOULD be present
        actual = secret_present

        if actual != expected:
            print(f"CONFIRMED — gitignored untracked file 'test.secret' is missing from snapshot. "
                  f"present={secret_present}, normal_untracked_present={normal_present}, "
                  f"tracked_present={tracked_present}")
        else:
            print(f"NOT CONFIRMED — gitignored untracked file 'test.secret' was present in snapshot. "
                  f"secret_present={secret_present}, normal_untracked_present={normal_present}, "
                  f"tracked_present={tracked_present}")

    finally:
        # Clean up: remove the snapshot worktree and the temp repo
        if snapshot_dir and os.path.exists(snapshot_dir):
            parent = os.path.dirname(snapshot_dir)
            if os.path.exists(parent):
                shutil.rmtree(parent, ignore_errors=True)
        shutil.rmtree(tmp_root, ignore_errors=True)


if __name__ == "__main__":
    main()
```

### Probe Output

```
[Pipeline] Snapshot created at: /tmp/fm_agent_wt_testrepo_vqrce874/snapshot
[Pipeline] Snapshot is kept after the run. Remove with: git -C /tmp/bug_probe_nuyn9g__/testrepo worktree remove --force /tmp/fm_agent_wt_testrepo_vqrce874/snapshot
CONFIRMED — gitignored untracked file 'test.secret' is missing from snapshot. present=False, normal_untracked_present=True, tracked_present=True
```

# Bug Report: frozen_worktree

**Source file:** `/home/fancy/Projects_Vault/FM-Agent/fm_agent/extracted_functions/src/git-py/frozen_worktree.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

Yields the absolute path wt to a directory whose contents at yield time are a faithful snapshot of the proj_dir filesystem tree at the moment frozen_worktree was entered. Subsequent modifications to proj_dir are not reflected in the snapshot at wt. The snapshot construction never modifies the original proj_dir tree, index, or git state. If proj_dir is a git repository with at least one commit, the snapshot is a detached git worktree comprising HEAD, all uncommitted tracked edits, and all untracked files present in proj_dir at entry time, with entries matching names in exclude omitted from the git commit. If proj_dir is not a git repository with a valid HEAD, the snapshot is a recursive directory copy of proj_dir, with entries matching names in exclude omitted. When copy_excluded is true, each directory named in exclude that exists in proj_dir is recursively copied into the snapshot at wt after the git worktree or directory copy is constructed. The snapshot at wt persists after the context manager exits and is not automatically removed.

---

### Actual Behavior

On normal execution, the generator yields `wt`, a directory at `<temp_dir>/snapshot` where `<temp_dir> = tempfile.mkdtemp(prefix="fm_agent_wt_<repo_name>_")` and `<repo_name>` is derived from `proj_dir`. If `proj_dir` was a git repo with a HEAD commit (`is_git` true), then `wt` is a detached worktree for a new commit that captures the working tree (tracked edits + untracked files) at the time `git add -A` ran, with directories in `exclude` removed from the commit via `git rm --cached`. The original git state (`HEAD`, index, working tree) is unchanged. If `copy_excluded` is true, each excluded directory that existed in `proj_dir` and is absent from `wt` is recursively copied into `wt` as an untracked directory. If `proj_dir` was not a valid git repo with HEAD (`is_git` false), `wt` is a plain copy of `proj_dir` (directories in `exclude` skipped via `shutil.ignore_patterns`), and if `copy_excluded`, those directories are subsequently copied into `wt`. `<temp_dir>` persists after the yield (no automatic deletion). `proj_dir` is unmodified. Messages containing `wt` and cleanup instructions are printed to stdout. On exceptional execution (exception before the yield), `proj_dir` is unchanged, `<temp_dir>` exists but may contain partial artifacts, and `wt` may not exist or be incomplete.

Formally:
Let P = os.path.abspath(proj_dir), R = os.path.basename(P.rstrip(os.sep)) or "repo", B = tempfile.mkdtemp(prefix="fm_agent_wt_" + R + "_"), W = os.path.join(B, "snapshot"), G = (subprocess.run(["git", "-C", P, "rev-parse", "--verify", "HEAD"], check=True, capture_output=True, text=True) did not raise CalledProcessError). Then the outcome satisfies:
  (Normal yield W)  (Exception raised  no yield).
  If normal yield:
    G  
      (  I = os.path.join(B, "index") that is a valid git index 
         tree = output of _git("write-tree", env=env) 
         snap = output of _git("commit-tree", tree, "-p", "HEAD", "-m", "... 

---

## Code Evidence

Line 47:             _git("rm", "-r", "--cached", "--quiet", "--ignore-unmatch", "--",
Line 48:                  *exclude, env=env)

---

## Trigger Condition

The code uses 'git rm --cached' with only the top-level exclude names, so nested directories/files with the same name remain in the commit. The specification says 'entries matching names in exclude omitted', which requires omission of all such entries at any depth.

---

## How to trigger the bug

When `frozen_worktree` is called with `exclude=("fm_agent",)` on a git repository that contains both a top-level `fm_agent/` directory and a nested directory with the same name (e.g., `testdata/fm_agent/`), the `git rm --cached fm_agent` command only removes the top-level `fm_agent/` from the private index. The nested `testdata/fm_agent/` — whose path does not match the bare name `fm_agent` — remains in the index and is included in the snapshot commit, violating the specification that **all** entries matching names in exclude must be omitted.

### Inputs

| Parameter | Value |
|-----------|-------|
| `proj_dir` | Temporary git repo with a top-level `fm_agent/` and a nested `testdata/fm_agent/` |
| `exclude` | `("fm_agent",)` |
| `copy_excluded` | `False` |

### Expected (spec-correct) Output

The snapshot at `wt` should contain `testdata/` with NO `fm_agent/` subdirectory — the nested `fm_agent/` should be excluded at all depths.

### Actual (buggy) Output

The snapshot at `wt` contains `testdata/fm_agent/` with all its files (e.g., `nested.txt`). The nested directory was not removed by `git rm --cached fm_agent`.

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import os, sys, shutil, tempfile, subprocess
sys.path.insert(0, os.path.abspath("."))

from src.git import frozen_worktree

tmpdir = tempfile.mkdtemp(prefix="probe_fwt_")
repo_path = os.path.join(tmpdir, "repo")
os.makedirs(repo_path)

def git(*args):
    subprocess.run(["git", "-C", repo_path, *args], check=True,
                   capture_output=True, text=True)

git("init")
git("config", "user.name", "test")
git("config", "user.email", "test@example.com")

# top-level exclude dir
os.makedirs(os.path.join(repo_path, "fm_agent"))
with open(os.path.join(repo_path, "fm_agent", "top.txt"), "w") as f:
    f.write("x")
# NESTED exclude dir — this should be excluded but LEAKS
os.makedirs(os.path.join(repo_path, "testdata", "fm_agent"))
with open(os.path.join(repo_path, "testdata", "fm_agent", "nested.txt"), "w") as f:
    f.write("x")

with open(os.path.join(repo_path, "regular.txt"), "w") as f:
    f.write("x")

git("add", ".")
git("commit", "-m", "init")

with frozen_worktree(repo_path, exclude=("fm_agent",), copy_excluded=False) as wt:
    leak = os.path.isdir(os.path.join(wt, "testdata", "fm_agent"))
    print("LEAK DETECTED" if leak else "NO LEAK")
    # actual (buggy) output: "LEAK DETECTED"
    # expected (correct) output: "NO LEAK"
```

---

## Probe Script

```python
"""Probe script for bug: src--git-py--frozen_worktree

The bug claim: frozen_worktree() uses `git rm --cached` with only top-level
exclude names (e.g. "fm_agent"), so nested directories/files with the same
name are NOT removed from the commit and leak into the snapshot.

This script creates a temporary git repo with:
  - A top-level fm_agent/ dir (should be excluded)
  - A nested testdata/fm_agent/ dir (should ALSO be excluded per spec)
then calls frozen_worktree() and checks whether the nested fm_agent/ leaks.
"""

import os
import sys
import shutil
import tempfile
import subprocess

# ---------------------------------------------------------------------------
# Must import from the public entry point
# ---------------------------------------------------------------------------
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from src.git import frozen_worktree

# ---------------------------------------------------------------------------
# Build a fresh temporary git repo with the trigger structure
# ---------------------------------------------------------------------------
tmpdir = tempfile.mkdtemp(prefix="probe_fwt_")
repo_path = os.path.join(tmpdir, "repo")
os.makedirs(repo_path)

def git(*args):
    subprocess.run(["git", "-C", repo_path, *args], check=True,
                   capture_output=True, text=True)

git("init")
git("config", "user.name", "test")
git("config", "user.email", "test@example.com")

# Create the top-level excluded directory (fm_agent/)
os.makedirs(os.path.join(repo_path, "fm_agent"))
with open(os.path.join(repo_path, "fm_agent", "top_level.txt"), "w") as f:
    f.write("should be excluded")

# Create a NESTED directory with the same name (testdata/fm_agent/)
os.makedirs(os.path.join(repo_path, "testdata", "fm_agent"))
with open(os.path.join(repo_path, "testdata", "fm_agent", "nested.txt"), "w") as f:
    f.write("should ALSO be excluded but may leak")

# Create a regular file that should be present regardless
with open(os.path.join(repo_path, "regular.txt"), "w") as f:
    f.write("should be in snapshot")

# Initial commit so we have a HEAD
git("add", "testdata/")
git("add", "regular.txt")
git("add", "fm_agent/")
git("commit", "-m", "initial")

# ---------------------------------------------------------------------------
# Call frozen_worktree (set copy_excluded=False so excluded dirs are NOT
# copied back — we only care about what the git worktree commit contains)
# ---------------------------------------------------------------------------
result = "ERROR"
actual_detail = ""

try:
    with frozen_worktree(repo_path, exclude=("fm_agent",), copy_excluded=False) as wt:
        # Check: is the nested fm_agent/ present in the snapshot?
        nested_path = os.path.join(wt, "testdata", "fm_agent")
        top_level_path = os.path.join(wt, "fm_agent")
        regular_path = os.path.join(wt, "regular.txt")

        nested_exists = os.path.isdir(nested_path)

        if nested_exists:
            # BUG CONFIRMED: nested fm_agent/ leaked into snapshot
            result = "CONFIRMED"
            nested_files = os.listdir(nested_path)
            actual_detail = (
                f"nested fm_agent/ present in snapshot at {nested_path} "
                f"(contains: {nested_files}) — spec requires exclusion at all depths"
            )
        else:
            result = "NOT CONFIRMED"
            actual_detail = (
                "nested fm_agent/ was correctly excluded from snapshot"
            )

except Exception as e:
    result = "ERROR"
    actual_detail = str(e)

# ---------------------------------------------------------------------------
# Cleanup
# ---------------------------------------------------------------------------
shutil.rmtree(tmpdir, ignore_errors=True)

# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------
print(f"{result} — {actual_detail}")
```

### Probe Output

```
[Pipeline] Snapshot created at: /tmp/fm_agent_wt_repo_54som_02/snapshot
[Pipeline] Snapshot is kept after the run. Remove with: git -C /tmp/probe_fwt_frax15ct/repo worktree remove --force /tmp/fm_agent_wt_repo_54som_02/snapshot
CONFIRMED — nested fm_agent/ present in snapshot at /tmp/fm_agent_wt_repo_54som_02/snapshot/testdata/fm_agent (contains: ['nested.txt']) — spec requires exclusion at all depths
```

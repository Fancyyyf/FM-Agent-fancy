# Bug Report: _git

**Source file:** `/tmp/fm_agent_wt_FM-Agent_dlsr6ukl/snapshot/fm_agent/extracted_functions/src/git-py/_git.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- Returns the stdout output of the executed git subcommand with leading and trailing
    whitespace characters removed
  - The git subcommand is executed with proj_dir as the effective working directory
  - If the git subcommand exits with a non-zero status, subprocess.CalledProcessError is
    raised; the exception carries the command string, the non-zero exit code, and the
    captured stdout and stderr

---

### Actual Behavior

After executing the code block, one of the following holds: (1) The function `_git` returns normally, in which case the return value is the stripped standard output string (`stdout.strip()`) of the git subprocess run with the command line `['git', '-C', proj_dir] + args`, using `check=True`, `capture_output=True`, `text=True`, and any additional keyword arguments from `kwargs`. The git process has been executed inside the directory `proj_dir`, potentially modifying the file system and the Git repository state according to the semantics of the git subcommand composed by `args`. (2) The git subprocess terminates with a non-zero exit code, which causes `subprocess.run` to raise a `CalledProcessError` exception; the function does not return a value, and the exception propagates. (3) An exception other than `CalledProcessError` (e.g., `FileNotFoundError` if `git` is not available, `PermissionError`, etc.) is raised, and no return value is produced. In all cases, the function has no other side effects on the Python program state beyond the effects of the subprocess execution.

---

## Code Evidence

Line 3: ["git", "-C", proj_dir, *args]

---

## Trigger Condition

The specification requires the exception to carry 'the command string', but the code constructs a list of arguments and passes it to subprocess.run. Consequently, CalledProcessError.cmd is a list, not a single string.

---

## How to trigger the bug

Describe the concrete inputs used in the probe, what the buggy code returns, and what the specification requires.

### Inputs

| Parameter | Value |
|-----------|-------|
| `proj_dir` | A valid git repository directory (temp dir created by probe) |
| `args` | `["worktree", "add", "--detach", wt, snap]` (arguments composed by `frozen_worktree`) |
| `env` (via `GIT_INDEX_FILE`) | A non-existent directory path to force `git read-tree` failure |

### Expected (spec-correct) Output

`CalledProcessError.cmd` should be a **string** representing the command, e.g. `"git -C /path/to/repo read-tree HEAD"`.

### Actual (buggy) Output

`CalledProcessError.cmd` is a **list**: `['git', '-C', '/path/to/repo', 'read-tree', 'HEAD']`. This is because `_git` at `src/git.py:76-77` constructs `["git", "-C", proj_dir, *args]` (a list) and passes it directly to `subprocess.run(check=True)`, which stores the command argument verbatim in `CalledProcessError.cmd`.

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import os
import subprocess
import tempfile

from src.git import frozen_worktree

# Create a temp git repo
tmpdir = tempfile.mkdtemp()
repo_dir = os.path.join(tmpdir, "repo")
os.makedirs(repo_dir)
subprocess.run(["git", "init", repo_dir], capture_output=True)
subprocess.run(
    ["git", "-C", repo_dir, "commit", "--allow-empty", "-m", "init"],
    capture_output=True,
    env={**os.environ, "GIT_AUTHOR_NAME": "test", "GIT_AUTHOR_EMAIL": "t@t",
         "GIT_COMMITTER_NAME": "test", "GIT_COMMITTER_EMAIL": "t@t"},
)

# Set GIT_INDEX_FILE to a path in a non-existent directory to force failure
os.environ["GIT_INDEX_FILE"] = os.path.join(tmpdir, "nonexistent", "index")

try:
    with frozen_worktree(repo_dir) as wt:
        pass
except subprocess.CalledProcessError as e:
    print(f"cmd type: {type(e.cmd).__name__}")  # 'list'
    print(f"cmd value: {e.cmd}")                 # ['git', '-C', '...', 'read-tree', 'HEAD']
# actual (buggy) output: cmd is a list of strings
# expected (correct) output: cmd should be a single string
```

---

## Probe Script

```python
"""Probe: _git passes a list to subprocess.run, so CalledProcessError.cmd is
a list, not a string as the spec claims.

The _git function is a closure inside frozen_worktree(). We exercise it by
calling frozen_worktree with a valid git repo and an invalid GIT_INDEX_FILE
environment variable that causes git read-tree to fail with a non-zero exit,
triggering CalledProcessError from _git.
"""
import sys
import os
import subprocess
import tempfile
import shutil

# ── set up a temp git repo ──────────────────────────────────────────
tmpdir = tempfile.mkdtemp(prefix="fm_agent_probe_")
repo_dir = os.path.join(tmpdir, "repo")
os.makedirs(repo_dir)

subprocess.run(["git", "init", repo_dir], capture_output=True)
subprocess.run(["git", "-C", repo_dir, "commit", "--allow-empty", "-m", "init"],
               capture_output=True,
               env={**os.environ, "GIT_AUTHOR_NAME": "test", "GIT_AUTHOR_EMAIL": "t@t",
                    "GIT_COMMITTER_NAME": "test", "GIT_COMMITTER_EMAIL": "t@t"})

# ── import and call frozen_worktree ──────────────────────────────────
try:
    from src.git import frozen_worktree
except Exception as e:
    print(f"ERROR: import failed: {e}")
    sys.exit(1)

result = None
exception_data = None

try:
    # Set GIT_INDEX_FILE to a non-existent directory so git read-tree
    # fails. _git("read-tree", "HEAD", env=env) at line 90 will raise
    # CalledProcessError because check=True.
    os.environ["GIT_INDEX_FILE"] = os.path.join(tmpdir, "nonexistent", "index")

    with frozen_worktree(repo_dir) as wt:
        result = ("returned", wt)
except subprocess.CalledProcessError as e:
    exception_data = {
        "type": type(e).__name__,
        "cmd_type": type(e.cmd).__name__,
        "cmd_value": repr(e.cmd),
        "returncode": e.returncode,
    }
except Exception as e:
    exception_data = {
        "type": type(e).__name__,
        "msg": str(e),
    }
finally:
    os.environ.pop("GIT_INDEX_FILE", None)
    shutil.rmtree(tmpdir, ignore_errors=True)

# ── verdict ─────────────────────────────────────────────────────────
if exception_data is None:
    if result and result[0] == "returned":
        print(f"NOT CONFIRMED — frozen_worktree returned normally: {result[1]!r}")
    else:
        print(f"ERROR — unexpected flow")
    sys.exit(0)

if exception_data["type"] != "CalledProcessError":
    print(f"ERROR — unexpected exception type: {exception_data}")
    sys.exit(1)

cmd_type = exception_data["cmd_type"]
cmd_val = exception_data["cmd_value"]

# Spec says: "the exception carries the command string"
# Actual: cmd is a list because _git passes a list to subprocess.run
if cmd_type == "list":
    print(f"CONFIRMED — CalledProcessError.cmd is {cmd_type!r} ({cmd_val}), "
          f"not a string as the spec claims. "
          f"Code at src/git.py:76-77 constructs ['git', '-C', proj_dir, *args] "
          f"and passes it to subprocess.run(check=True).")
elif cmd_type == "str":
    print(f"NOT CONFIRMED — CalledProcessError.cmd is a string: {cmd_val}")
else:
    print(f"ERROR — unexpected cmd type: {cmd_type} ({cmd_val})")
```

### Probe Output

```
CONFIRMED — CalledProcessError.cmd is 'list' (['git', '-C', '/tmp/fm_agent_probe_87jngnld/repo', 'worktree', 'add', '--detach', '/tmp/fm_agent_wt_repo_k_saawu7/snapshot', 'baab82c69bb6a002d6c7b47b02e08d783097368c']), not a string as the spec claims. Code at src/git.py:76-77 constructs ['git', '-C', proj_dir, *args] and passes it to subprocess.run(check=True).
```

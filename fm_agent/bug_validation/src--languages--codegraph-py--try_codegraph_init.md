# Bug Report: try_codegraph_init

**Source file:** `/tmp/fm_agent_wt_FM-Agent_xyeqtgt6/snapshot/fm_agent/extracted_functions/src/languages/codegraph-py/try_codegraph_init.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- Returns None; never raises an exception.
  - When the `codegraph` executable is not found on the system PATH: returns
    immediately without creating, modifying, or removing any files under proj_dir.
  - When proj_dir/.codegraph/codegraph.db exists AND force is False: returns
    immediately; the existing index file and its parent directory are preserved.
  - Otherwise (force is True, or proj_dir/.codegraph/codegraph.db does not exist):
    - If a proj_dir/.codegraph/ directory exists, it is removed prior to
      rebuilding (recursively, with errors ignored).
    - `codegraph init` is executed with proj_dir as its working directory.
    - If `codegraph init` exits with code 0: proj_dir/.codegraph/codegraph.db
      exists after return and reflects the file tree of proj_dir at the time
      `codegraph init` was invoked.
    - If `codegraph init` exits with a non-zero code: a warning is logged
      whose message includes the first 300 characters of stderr; the function
      returns and the contents of proj_dir/.codegraph/ are unspecified.

---

### Actual Behavior

After the function returns, the following post-conditions hold regarding the project directory `proj_dir`:

1. The existence of the codegraph index database file `db = os.path.join(proj_dir, '.codegraph', 'codegraph.db')` satisfies:

   db_post_exists  ( (db_pre_exists  force = False)  (cmd_available  (force   db_pre_exists)  exit_code = 0) )

   where
     db_pre_exists = os.path.exists(db) before the call,
     db_post_exists = os.path.exists(db) after the call,
     cmd_available = the `codegraph` command identified by `_codegraph_cmd()` is present on PATH and does not raise `FileNotFoundError`,
     exit_code = return code of `subprocess.run([cmd, 'init'], ...)` if it runs (0 on success).

2. If `force` was True and `db_pre_exists` was True, the entire `.codegraph` directory was removed via `shutil.rmtree` before the command attempt.
3. The function never raises an exception; it handles missing executables and non-zero exit codes gracefully.
4. Informational messages are printed or logged as per lines 25,27,37,39-42.

---

## Code Evidence

Line 19: if os.path.exists(db_path):
Line 20:         if not force:
Line 21:             return
Line 24:         shutil.rmtree(codegraph_dir, ignore_errors=True)

---

## Trigger Condition

The code removes the existing .codegraph directory (line 24) before checking whether the 'codegraph' executable exists (line 31). When the executable is missing, a FileNotFoundError is caught (line 34-35) and the function returns, but the removal has already occurred. This violates the specification requirement that when the executable is not found, the function must return immediately without creating, modifying, or removing any files under proj_dir.

---

## How to trigger the bug

The bug occurs when `try_codegraph_init` is called with `force=True` on a project directory that has a pre-existing `.codegraph/codegraph.db`, and the `codegraph` executable is not available on the system. The function removes the `.codegraph` directory at line 526 (source line 24 in extracted function) before discovering at line 532-537 (lines 30-35) that the command cannot be found, leaving the directory destroyed despite the spec requiring no file modifications when the executable is missing.

### Inputs

| Parameter | Value |
|-----------|-------|
| `proj_dir` | Path to a temporary directory containing `.codegraph/codegraph.db` |
| `force` | `True` |

### Expected (spec-correct) Output

`.codegraph/` directory preserved (function returns without modifying any files under `proj_dir`)

### Actual (buggy) Output

`.codegraph/` directory is removed by `shutil.rmtree()` before the `FileNotFoundError` is caught

### How to Reproduce

1. Navigate to the repo root.
2. Ensure the `codegraph` executable is not found (monkey-patch `_codegraph_cmd` to return a nonexistent path).
3. Run the following snippet (uses the package entry point):

```python
from src.languages.codegraph import try_codegraph_init

# Monkey-patch _codegraph_cmd so codegraph is "not found"
import src.languages.codegraph as cg
cg._codegraph_cmd = lambda: "/nonexistent/codegraph"

# Create a temp project dir with .codegraph/codegraph.db
import tempfile, os
tmp = tempfile.mkdtemp()
os.makedirs(os.path.join(tmp, ".codegraph"))
with open(os.path.join(tmp, ".codegraph", "codegraph.db"), "w") as f:
    f.write("mock")

# Call with force=True — this will remove .codegraph/ then fail to find codegraph
try_codegraph_init(proj_dir=tmp, force=True)

# .codegraph/ is gone — violates spec (should be preserved)
print(os.path.exists(os.path.join(tmp, ".codegraph")))  # actual (buggy) output: False
# expected (correct) output: True
```

---

## Probe Script

```python
"""Probe script for bug: try_codegraph_init removes .codegraph before checking executable.

Bug ID: src--languages--codegraph-py--try_codegraph_init

The function try_codegraph_init(proj_dir, force=True) calls shutil.rmtree()
at line 526 to remove the .codegraph directory BEFORE checking whether the
codegraph executable exists (line 530-537). When codegraph is missing, a
FileNotFoundError is caught and the function returns — but the directory
has already been removed, violating the spec that requires no file
modifications when the executable is not found.
"""

import os
import sys
import tempfile
import shutil

# Ensure we can import from the repo root
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

import src.languages.codegraph as codegraph_module
from src.languages.codegraph import try_codegraph_init

# Monkey-patch _codegraph_cmd to simulate "codegraph not installed".
# This ensures subprocess.run([cmd, "init"], ...) raises FileNotFoundError
# regardless of whether codegraph is actually present on the system.
_original_codegraph_cmd = codegraph_module._codegraph_cmd
codegraph_module._codegraph_cmd = lambda: "/nonexistent/codegraph_binary_not_found"

exit_code = 0
temp_dir = None
result_msg = ""

try:
    # Create a temporary project directory with a pre-existing .codegraph/codegraph.db
    temp_dir = tempfile.mkdtemp(prefix="fmagent_probe_")
    codegraph_dir = os.path.join(temp_dir, ".codegraph")
    os.makedirs(codegraph_dir, exist_ok=True)
    db_path = os.path.join(codegraph_dir, "codegraph.db")
    with open(db_path, "w") as f:
        f.write("mock codegraph database\n")

    # Verify pre-condition: .codegraph directory and codegraph.db exist before the call
    assert os.path.isdir(codegraph_dir), (
        "Pre-condition failed: .codegraph dir does not exist"
    )
    assert os.path.exists(db_path), (
        "Pre-condition failed: codegraph.db does not exist"
    )

    # Call the function with force=True — the buggy path (line 526 removes dir
    # BEFORE line 530 checks for the codegraph executable)
    try_codegraph_init(proj_dir=temp_dir, force=True)

    # After the call, check whether .codegraph was preserved (spec-correct)
    # or removed (buggy behavior)
    dir_exists_after = os.path.isdir(codegraph_dir)

    if dir_exists_after:
        result_msg = (
            "NOT CONFIRMED — .codegraph directory was preserved (spec-compliant). "
            "The function left the directory intact when codegraph was unavailable."
        )
    else:
        result_msg = (
            "CONFIRMED — .codegraph directory was removed before checking for "
            "codegraph executable. Spec violation: the spec requires that when "
            "the codegraph executable is not found, the function returns "
            "immediately without creating, modifying, or removing any files "
            "under proj_dir."
        )

except Exception as exc:
    result_msg = f"ERROR: {type(exc).__name__}: {exc}"
    exit_code = 1

finally:
    # Restore original _codegraph_cmd
    codegraph_module._codegraph_cmd = _original_codegraph_cmd
    # Cleanup temp directory
    if temp_dir is not None and os.path.exists(temp_dir):
        shutil.rmtree(temp_dir, ignore_errors=True)

print(result_msg)
sys.exit(exit_code)
```

### Probe Output

```
[Pipeline] Rebuilding codegraph index for current working tree...
CONFIRMED — .codegraph directory was removed before checking for codegraph executable. Spec violation: the spec requires that when the codegraph executable is not found, the function returns immediately without creating, modifying, or removing any files under proj_dir.
```

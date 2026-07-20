# Bug Report: try_codegraph_init

**Source file:** `src/languages/codegraph.py`
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

After execution, no unhandled exceptions propagate. Let init_db_pre be the file `<proj_dir>/.codegraph/codegraph.db`. 

If init_db_pre exists and force is False, the function returns immediately with no side effects (filesystem unchanged, no output). 

Otherwise (init_db_pre does not exist, or force is True): 
- If init_db_pre exists (and force True), a removal of `<proj_dir>/.codegraph` is attempted via `shutil.rmtree` with `ignore_errors=True`, and the message "[Pipeline] Rebuilding codegraph index for current working tree..." is printed. The directory and its contents may or may not be fully removed; removal errors are silently ignored. 
- If init_db_pre does not exist, the message "[Pipeline] Building codegraph index..." is printed and no removal is attempted. 
- Then a subprocess `['codegraph', 'init']` is executed in `proj_dir` with `capture_output=True`. 
   - If the `codegraph` executable is not found (`FileNotFoundError`), the function returns silently; no further output; the filesystem state is whatever resulted from the earlier steps. 
   - If `codegraph` runs: 
        - On exit code 0, the message "[Pipeline] codegraph index built." is printed. The `<proj_dir>/.codegraph` directory and the file `codegraph.db` are expected to exist and reflect the current working tree (as per `codegraph init` semantics). 
        - On any non-zero exit, a warning is logged with the first 300 characters of `stderr`; the index state is unspecified (typically not built or left in an error state). 

The function never raises exceptions; `FileNotFoundError` is caught and non-zero returns are not re-raised.

---

## Code Evidence

Line 19: if os.path.exists(db_path):

---

## Trigger Condition

Spec requires removal of the .codegraph directory whenever it exists and the function is not returning early (i.e., when force is False but codegraph.db does not exist, the specification's 'Otherwise' case applies and mandates removal before rebuilding). The code's check at Line 19 only removes the directory if the codegraph.db file exists, failing to remove it when the .codegraph directory exists without the db file, which violates the specification.

---

## How to trigger the bug

Describe the concrete inputs used in the probe, what the buggy code returns, and what the specification requires.

### Inputs

| Parameter | Value |
|-----------|-------|
| proj_dir | A temp directory containing `.codegraph/` with a marker file but NO `codegraph.db` |
| force | `False` |

### Expected (spec-correct) Output

The `.codegraph/` directory should be removed before `codegraph init` runs. The marker file should be gone.

### Actual (buggy) Output

The `.codegraph/` directory is NOT removed. The marker file persists. `codegraph init` runs but does not clear the old directory contents.

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import os, tempfile, sys
sys.path.insert(0, '/tmp/fm_agent_wt_FM-Agent_dlsr6ukl/snapshot')
from src.languages.codegraph import try_codegraph_init

tmp = tempfile.mkdtemp()
codegraph_dir = os.path.join(tmp, ".codegraph")
os.makedirs(codegraph_dir)
marker = os.path.join(codegraph_dir, "marker.txt")
with open(marker, "w") as f:
    f.write("exists")

try_codegraph_init(tmp, force=False)  # BUG: .codegraph/ not removed

print("marker still exists:", os.path.exists(marker))
# actual (buggy) output: marker still exists: True
# expected (correct) output: marker still exists: False
```

---

## Probe Script

```python
import sys
sys.path.insert(0, '/tmp/fm_agent_wt_FM-Agent_dlsr6ukl/snapshot')

import os
import tempfile
import shutil

try:
    from src.languages.codegraph import try_codegraph_init

    # Bug trigger: .codegraph/ directory exists but codegraph.db does NOT exist.
    # Spec's "Otherwise" case applies (codegraph.db missing) → requires directory removal.
    # Code at line 400 only checks os.path.exists(db_path), so it skips to the else
    # branch without removing the existing .codegraph/ directory.

    tmp = tempfile.mkdtemp()
    codegraph_dir = os.path.join(tmp, ".codegraph")
    os.makedirs(codegraph_dir)
    marker_file = os.path.join(codegraph_dir, "marker.txt")
    with open(marker_file, "w") as f:
        f.write("this marker proves the directory was not removed")

    # spec_claim: when codegraph.db doesn't exist (Otherwise case), if .codegraph/
    #   exists, it must be removed before rebuilding.
    # actual_behavior (bug): directory is NOT removed because the code only checks
    #   for db_path existence.
    try_codegraph_init(tmp, force=False)

    # If the spec was followed: marker_file should be gone (rmtree deleted .codegraph/)
    # If the bug exists: marker_file still there (dir was never removed)
    marker_exists = os.path.exists(marker_file)
    expected = False  # spec requires removal
    passed = marker_exists != expected  # True → bug reproduced

except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)
finally:
    # Cleanup temp directory
    try:
        shutil.rmtree(tmp, ignore_errors=True)
    except Exception:
        pass

if passed:
    print(f'CONFIRMED — marker file {"still exists (.codegraph/ not removed by function)" if marker_exists else "unexpectedly missing"} | spec requires removal of .codegraph/ when codegraph.db is absent')
else:
    print(f'NOT CONFIRMED — marker file was {"removed (spec correct)" if not marker_exists else "still exists but expected was confused"}')
```

### Probe Output

```
[Pipeline] Building codegraph index...
[Pipeline] codegraph index built.
CONFIRMED — marker file still exists (.codegraph/ not removed by function) | spec requires removal of .codegraph/ when codegraph.db is absent
```

# Bug Report: _setup_incremental_logging

**Source file:** `/home/fancy/Projects_Vault/FM-Agent/fm_agent/extracted_functions/src/incremental_reasoner-py/_setup_incremental_logging.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

The Python root logger is configured to emit all records at the INFO level and above to two destinations: a timestamped log file at work_dir/incremental_<YYYYmmdd_HHMMSS>.log (the timestamp is captured at the moment of call) and stdout, both using the format "%(asctime)s %(levelname)s %(name)s: %(message)s". Any handlers previously attached to the root logger are removed before the new ones are installed, so repeated invocations do not duplicate log entries. sys.stdout is replaced with an object that writes every string received via its write method (including all output from print()) to both the original stdout stream and the same log file. The wrapping is idempotent: if a prior call already wrapped sys.stdout, the original stdout is recovered before wrapping, so repeated calls produce exactly one copy of each printed line in both destinations. Returns the absolute path of the created log file.

---

### Actual Behavior

work_dir exists and is writable; a new file is created at path log_path = os.path.join(work_dir, 'incremental_' + timestamp + '.log') where timestamp is datetime.now().strftime('%Y%m%d_%H%M%S') at call time; the function returns log_path; the root logger has level INFO, all prior handlers removed, and two handlers added: a FileHandler to log_path and a StreamHandler to the original console stream (sys.stdout._console if present else initial sys.stdout); sys.stdout is replaced by a _StdoutTee(console_stream, file_handler.stream); no exception propagates.

---

## Code Evidence

Line 26: log_path = os.path.join(work_dir, f"incremental_{timestamp}.log")
Line 47: return log_path

---

## Trigger Condition

The specification requires returning the absolute path of the log file, but the code returns the joined path as-is, which is relative if work_dir is relative.

---

## How to trigger the bug

When `work_dir` is a relative path (e.g., `"my_workdir"`), `os.path.join()` produces a relative log path (e.g., `"my_workdir/incremental_20260728_121457.log"`), and the function returns it directly without calling `os.path.abspath()`. The specification requires the return value to be an absolute path.

### Inputs

| Parameter | Value |
|-----------|-------|
| `work_dir` | `"my_workdir"` (a relative path) |

### Expected (spec-correct) Output

`<absolute path to the log file>`

### Actual (buggy) Output

`"my_workdir/incremental_<YYYYmmdd_HHMMSS>.log"` (a relative path)

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import os
import sys
sys.path.insert(0, '.')
from src.incremental_reasoner import _setup_incremental_logging

log_path = _setup_incremental_logging("my_workdir")
print(repr(log_path))
# actual (buggy) output: 'my_workdir/incremental_20260728_121457.log'
# expected (correct) output: '/absolute/path/to/my_workdir/incremental_20260728_121457.log'
```

---

## Probe Script

```python
import os
import sys
import shutil
import tempfile
import logging

old_cwd = os.getcwd()
workspace = tempfile.mkdtemp(prefix="probe_")

try:
    # Chdir into the temp workspace so that os.makedirs with a relative path
    # creates directories inside the temp area, not in the repo.
    os.chdir(workspace)
    sys.path.insert(0, old_cwd)

    from src.incremental_reasoner import _setup_incremental_logging

    relative_work_dir = "my_workdir"
    log_path = _setup_incremental_logging(relative_work_dir)

    # Restore stdout immediately in case the function wrapped it.
    if hasattr(sys.stdout, '_console'):
        sys.stdout = sys.stdout._console

    # Clean up logging handlers the function installed.
    root = logging.getLogger()
    for handler in list(root.handlers):
        handler.close()
        root.removeHandler(handler)

    # The spec requires returning the *absolute* path of the log file.
    expected = os.path.abspath(log_path)
    actual = log_path

    # Bug confirmed if the returned path is not absolute.
    bug_confirmed = actual != expected

    if bug_confirmed:
        print(f'CONFIRMED — actual: {actual!r} | expected: {expected!r}')
    else:
        print(f'NOT CONFIRMED — actual matched expected: {actual!r}')

except Exception as e:
    import traceback
    traceback.print_exc()
    print(f'ERROR: {e}')
    sys.exit(1)

finally:
    os.chdir(old_cwd)
    shutil.rmtree(workspace, ignore_errors=True)
```

### Probe Output

```
CONFIRMED — actual: 'my_workdir/incremental_20260728_121457.log' | expected: '/tmp/probe_oh62vad5/my_workdir/incremental_20260728_121457.log'
```

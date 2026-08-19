# Bug Report: batch_extract

**Source file:** `src/languages/erlang.py`
**Verdict:** MISMATCH
**Confirmation status:** not_confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

Returns a dictionary whose keys are absolute file paths (strings) of Erlang source files and whose values are lists of (function_id: str, body: str) pairs. Each function_id is a canonicalized, module-qualified name usable as an FQN. Each body is the verbatim source text of that function as extracted from the source file. Returns an empty dict when the Erlang Language Platform backend is unavailable or when proj_dir contains no extractable Erlang functions.

---

### Actual Behavior

If the function returns normally, the returned value is a dictionary where each key is an absolute file path string referring to an Erlang source file within the directory specified by proj_dir, and each value is a list of tuples (function_id, body) extracted by the analysis. If an exception occurs (for example, from _analysis_or_empty due to invalid proj_dir, I/O errors, or because the result of _analysis_or_empty lacks a `functions` attribute), the exception propagates and the function does not return a value.

---

## Code Evidence

Line 3: return _analysis_or_empty(proj_dir).functions

---

## Trigger Condition

The specification requires that the function returns an empty dict when the Erlang Language Platform backend is unavailable. However, the code directly returns the .functions attribute of _analysis_or_empty without any exception handling. If the backend is unavailable, _analysis_or_empty may raise an exception (as indicated by the example in Condition A), which would propagate and prevent the function from returning an empty dict. This violates the specification's requirement for that scenario.

---

## How to trigger the bug

Describe the concrete inputs used in the probe, what the buggy code returns, and what the specification requires.

### Inputs

| Parameter | Value |
|-----------|-------|
| proj_dir | /tmp/erlang_probe_<random> (directory containing a dummy.erl file) |

### Expected (spec-correct) Output

`{}` (empty dict, because ELP backend is not installed)

### Actual (buggy) Output

`{}` — the function returned an empty dict as specified. No exception was raised.

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import os, sys, tempfile
_repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _repo_root)
from src.languages.erlang import batch_extract

tmpdir = tempfile.mkdtemp(prefix="erlang_probe_")
with open(os.path.join(tmpdir, "dummy.erl"), "w") as f:
    f.write("-module(dummy).\n-export([hello/0]).\nhello() -> world.\n")
result = batch_extract(tmpdir)
# actual (buggy) output: {}
# expected (correct) output: {}
```

---

## Probe Script

```python
"""Probe script for bug: batch_extract does not catch exceptions from _analysis_or_empty.

Spec claim: Returns an empty dict when the Erlang Language Platform backend is unavailable.
Actual: If _analysis_or_empty raises, batch_extract propagates the exception.

Trigger: Create a temp directory with an .erl file, call batch_extract() on it
when ELP is not installed. The backend should be unavailable, triggering the
exception path.
"""

import os
import sys
import tempfile
import shutil

# Add repo root to Python path so `src.languages.erlang` is importable
_repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

try:
    from src.languages.erlang import batch_extract

    # Create a temp directory with an .erl file inside to force the backend path.
    # If there are no .erl files, _analyze_project_uncached returns early without
    # ever trying to start ELP. We need at least one .erl file to exercise the
    # backend-unavailable path.
    tmpdir = tempfile.mkdtemp(prefix="erlang_probe_")
    try:
        erl_file = os.path.join(tmpdir, "dummy.erl")
        with open(erl_file, "w") as f:
            f.write("-module(dummy).\n-export([hello/0]).\nhello() -> world.\n")

        result = batch_extract(tmpdir)

        # If we reach here, no exception was raised — the function handled it
        print(f"NOT CONFIRMED — batch_extract(...) returned: {result!r} (no exception raised)")
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)

except FileNotFoundError as e:
    # _analysis_or_empty catches Exception; FileNotFoundError is an OSError/Exception
    # If it still propagates, the bug is confirmed
    print(f"CONFIRMED — batch_extract(...) raised FileNotFoundError instead of returning {{}}: {e}")
except Exception as e:
    # Any other exception propagating is also a violation of the spec
    print(f"CONFIRMED — batch_extract(...) raised {type(e).__name__} instead of returning {{}}: {e}")
```

### Probe Output

```
WARNING:root:ELP Erlang analysis unavailable for /tmp/erlang_probe_ov_1w_vt: [Errno 2] No such file or directory: 'elp'
NOT CONFIRMED — batch_extract(...) returned: {} (no exception raised)
```

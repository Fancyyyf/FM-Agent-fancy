# Bug Report: function_spans

**Source file:** `src/languages/erlang-py/function_spans.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- When the Erlang Language Platform (ELP) backend is available and has indexed
    filepath, returns a list of (func_name, start_line, end_line) tuples for every
    function definition found in the file
  - start_line and end_line are 0-based inclusive line numbers within the file
  - Returns None when the ELP backend is unavailable or filepath has not been
    indexed, signaling the caller to fall back to a regex-based extractor
  - The returned list is empty when filepath contains no function definitions and
    the backend is available

---

### Actual Behavior

The function computes path = os.path.abspath(filepath) and returns _analysis_or_empty(proj_dir).spans.get(path). The return value is either a list of (func_name: str, start_line: int, end_line: int) tuples, each representing a function's 0based inclusive sourceline span, or None if the path is not present in the spans mapping. Formally: let  p = os.path.abspath(filepath),  s = _analysis_or_empty(proj_dir).spans.  Then result = s.get(p).  result is None  (result is a list   t  result : t = (name, start, end)  name is str  start, end    start  end).

---

## Code Evidence

Line 4: return _analysis_or_empty(proj_dir).spans.get(path)

---

## Trigger Condition

When the ELP backend is available and a file has been indexed but contains no function definitions, the specification requires returning an empty list. However, the code returns None because the spans dictionary may lack an entry for that file (it only stores files that have at least one function). The .get call returns None in that case, violating the required empty-list response.

---

## How to trigger the bug

When ELP backend is available and indexes a project containing an `.erl` file with zero function definitions (e.g. a module that only imports headers or defines types/macros), `function_spans` returns `None` instead of the spec-required `[]`. The root cause is in `_analyze_project_uncached` (erlang.py lines 576-578): the `spans` dict only receives an entry when `file_functions` is non-empty. Files with no functions are silently absent from the dict, so `.get(path)` falls through to its `None` default.

### Inputs

| Parameter | Value |
|-----------|-------|
| `proj_dir` | Path to a project directory with `.erl` files that ELP can index |
| `filepath` | Path to an `.erl` file inside `proj_dir` that contains no function definitions |

### Expected (spec-correct) Output

`[]` (empty list)

### Actual (buggy) Output

`None`

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import os, tempfile
from src.languages.erlang import function_spans, ErlangAnalysis
from unittest import mock

# Create an .erl file with no function definitions
tmp = tempfile.mkdtemp(prefix="erlang_")
erl = os.path.join(tmp, "empty.erl")
with open(erl, "w") as f:
    f.write("% No functions defined\n")

# Simulate ELP available but no functions found in the file
analysis = ErlangAnalysis(functions={}, edges={})
with mock.patch("src.languages.erlang._analysis_or_empty", return_value=analysis):
    result = function_spans(tmp, erl)
# actual (buggy) output: None
# expected (correct) output: []
print(result)  # None
```

---

## Probe Script

```python
"""Probe script for bug: src--languages--erlang-py--function_spans

Bug: function_spans returns None when ELP is available and a file has been
indexed but contains no function definitions.  The spec requires an empty
list ([]) in that case.

Because ELP is not installed in this environment, we mock _analysis_or_empty
to return a controlled ErlangAnalysis whose spans dict simulates the exact
condition: ELP is available (non-empty analysis structure) but the target
file produced zero function symbols, so no entry was stored in the spans
mapping.  The .get() call then falls through to its None default — the bug.
"""
import sys
import os
import tempfile
import shutil
import unittest.mock as mock

# Ensure repo root is on sys.path so "from src..." resolves
_script_dir = os.path.dirname(os.path.abspath(__file__))
_repo_root = os.path.dirname(os.path.dirname(_script_dir))
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

try:
    from src.languages.erlang import function_spans, ErlangAnalysis

    # Create a minimal temp project with a zero-function .erl file.
    tmp_dir = tempfile.mkdtemp(prefix="erlang_test_")
    try:
        empty_erl = os.path.join(tmp_dir, "empty.erl")
        with open(empty_erl, "w") as f:
            f.write("% This Erlang module defines no functions\n")

        # Build a mock ErlangAnalysis that simulates "ELP available, file
        # indexed, but no function definitions found".  In the real
        # _analyze_project_uncached the spans dict only receives an entry
        # when file_functions is non-empty (line 576-578).  An empty file
        # therefore produces no spans entry.
        mock_analysis = ErlangAnalysis(
            functions={},    # empty — no functions found
            edges={},        # empty — no call graph
            # spans is intentionally left as its default (empty dict) to
            # match the real behaviour when a file has zero functions.
        )

        with mock.patch(
            "src.languages.erlang._analysis_or_empty",
            return_value=mock_analysis,
        ):
            actual = function_spans(tmp_dir, empty_erl)

        # SPEC says: "The returned list is empty when filepath contains no
        # function definitions and the backend is available."
        expected = []
        passed = actual != expected  # True → bug reproduced

        if passed:
            print(
                f"CONFIRMED — actual: {actual!r} | expected: {expected!r}"
            )
        else:
            print(
                f"NOT CONFIRMED — actual matched expected: {actual!r}"
            )
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)

except Exception as e:
    import traceback
    traceback.print_exc()
    print(f"ERROR: {e}")
    sys.exit(1)
```

### Probe Output

```
CONFIRMED — actual: None | expected: []
```

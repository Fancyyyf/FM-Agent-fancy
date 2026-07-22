# Bug Report: function_spans

**Source file:** `/tmp/fm_agent_wt_FM-Agent_xyeqtgt6/snapshot/fm_agent/extracted_functions/src/languages/c-py/function_spans.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- Returns None when a codegraph instance cannot be initialized from proj_dir
  - Otherwise returns a list of (function_name, start_idx, end_idx) tuples for every
    function defined in the C source file at filepath, where start_idx and end_idx
    are 0-indexed inclusive line numbers

---

### Actual Behavior

After execution, the function returns either `None` or a list of `(name, start_idx, end_idx)` tuples. Formally, let `cg = CodeGraphExtractor.from_proj_dir(proj_dir)`. If `cg is None`, the return value is `None`. Otherwise, the return value is `cg.get_function_spans("c", filepath)`. Consequently, the overall return value is `None` if and only if the code graph is unavailable for `proj_dir` or the call to `get_function_spans` returns `None` (e.g., language key not recognized, file not indexed, no definitions, or path resolution failure). If the return value is not `None`, it is a Python list `L` where each element is a tuple `(name: str, start_idx: int, end_idx: int)` such that `0 <= start_idx <= end_idx`, the tuples represent all function/method definitions detected in the C source file pointed to by `filepath`, `name` is a class-qualified identifier, and `L` is sorted by ascending `start_idx`. No side effects are visible to the caller beyond the value returned.

---

## Code Evidence

Line 8: return cg.get_function_spans("c", filepath) if cg else None

---

## Trigger Condition

The specification states that None is returned only when a codegraph instance cannot be initialized from proj_dir; otherwise a list (possibly empty) of function tuples must be returned. The code, however, also returns None when get_function_spans returns None for reasons other than initialization failure (e.g., the file has no definitions). This violates the specification because for valid proj_dir and a C file with no functions, the code returns None instead of an empty list.

---

## How to trigger the bug

Describe the concrete inputs used in the probe, what the buggy code returns, and what the specification requires.

### Inputs

| Parameter | Value |
|-----------|-------|
| proj_dir | `"/fake/proj_dir"` (valid directory where codegraph initializes successfully) |
| filepath | `"/fake/proj_dir/empty.c"` (a C source file with no function definitions) |

### Expected (spec-correct) Output

`[]` (an empty list — the file has no functions, but codegraph was initialized successfully)

### Actual (buggy) Output

`None` (returned because `get_function_spans` returns `None` when the file has no definitions, and the code passes this through instead of converting it to an empty list)

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
from unittest.mock import patch, MagicMock
from src.languages.c import function_spans

proj_dir = "/fake/proj_dir"
filepath = "/fake/proj_dir/empty.c"

mock_cg = MagicMock()
mock_cg.get_function_spans.return_value = None

with patch("src.languages.c.CodeGraphExtractor.from_proj_dir", return_value=mock_cg):
    result = function_spans(proj_dir, filepath)

# actual (buggy) output: None
# expected (correct) output: []
```

---

## Probe Script

```python
import sys
import os
from unittest.mock import patch, MagicMock

# The probe is run from the repo root, so cwd is the import base.
sys.path.insert(0, os.getcwd())


def main():
    try:
        from src.languages.c import function_spans

        proj_dir = "/fake/proj_dir"
        filepath = "/fake/proj_dir/empty.c"

        # Create a mock CodeGraphExtractor instance
        mock_cg = MagicMock()
        # get_function_spans returns None (simulating a file with no definitions)
        mock_cg.get_function_spans.return_value = None

        # Patch from_proj_dir to return our mock (valid codegraph, not None)
        with patch("src.languages.c.CodeGraphExtractor.from_proj_dir", return_value=mock_cg):
            actual = function_spans(proj_dir, filepath)

        # Spec: for valid codegraph, return a LIST (possibly empty), never None.
        # Bug: returns None because get_function_spans returns None for a file
        # with no definitions.
        expected = []  # spec-correct: empty list when file has no functions
        passed = actual is None  # True = bug reproduced (got None instead of [])

        if passed:
            print(f"CONFIRMED — actual: {actual!r} | expected: {expected!r}")
        else:
            print(f"NOT CONFIRMED — actual matched expected: {actual!r}")

    except Exception as e:
        import traceback
        traceback.print_exc(file=sys.stderr)
        print(f"ERROR: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
```

### Probe Output

```
CONFIRMED — actual: None | expected: []
```

# Bug Report: function_spans

**Source file:** `src/languages/javascript.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- Returns None when the codegraph backend is unavailable for the project, or when the
    backend exists but does not index the given file.
  - Otherwise returns a list of (name, start_idx, end_idx) tuples, one per function
    defined in the file.
  - start_idx and end_idx are 0-indexed inclusive line numbers.
  - The list is ordered by appearance (ascending start_idx).
  - The list is empty when no functions are defined in the file.

---

### Actual Behavior

If CodeGraphExtractor.from_proj_dir(proj_dir) returns None, function_spans returns None. Otherwise, let cg be that returned CodeGraphExtractor; if cg.get_function_spans("javascript", filepath) returns None, then function_spans returns None; otherwise, it returns the list of (name, start_idx, end_idx) tuples with 0-indexed inclusive line numbers. Formally: let R = function_spans(proj_dir, filepath), C = CodeGraphExtractor.from_proj_dir(proj_dir). Then (C = None  R = None)  ((C  None  C.get_function_spans("javascript", filepath) = None)  R = None)  ((C  None  C.get_function_spans("javascript", filepath)  None)  R = C.get_function_spans("javascript", filepath)).

---

## Code Evidence

Line 8: return cg.get_function_spans("javascript", filepath) if cg else None

---

## Trigger Condition

The specification requires the returned list to be ordered by ascending start_idx. The code simply returns the raw list from cg.get_function_spans without sorting. The post-condition of get_function_spans does not guarantee ordering, so a valid input where the codegraph backend returns an unordered list leads to a specification violation.

---

## How to trigger the bug

The function passes through whatever `cg.get_function_spans()` returns without ensuring the result is sorted by `start_idx`. When the backend returns spans in any order other than ascending start_idx, the output violates the specification's ordering requirement.

### Inputs

| Parameter | Value |
|-----------|-------|
| `proj_dir` | `"/fake/proj_dir"` |
| `filepath` | `"/fake/file.js"` |

The mock backend returns `[("func_c", 40, 52), ("func_a", 5, 18), ("func_b", 22, 35)]` — spans deliberately out of ascending start_idx order.

### Expected (spec-correct) Output

`[('func_a', 5, 18), ('func_b', 22, 35), ('func_c', 40, 52)]`

### Actual (buggy) Output

`[('func_c', 40, 52), ('func_a', 5, 18), ('func_b', 22, 35)]`

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
from unittest.mock import MagicMock, patch

UNSORTED_SPANS = [
    ("func_c", 40, 52),
    ("func_a", 5,  18),
    ("func_b", 22, 35),
]

mock_cg = MagicMock()
mock_cg.get_function_spans.return_value = UNSORTED_SPANS

with patch('src.languages.javascript.CodeGraphExtractor') as MockExtractorClass:
    MockExtractorClass.from_proj_dir.return_value = mock_cg
    from src.languages.javascript import function_spans
    result = function_spans('/fake/proj_dir', '/fake/file.js')

# actual (buggy) output: [('func_c', 40, 52), ('func_a', 5, 18), ('func_b', 22, 35)]
# expected (correct) output: [('func_a', 5, 18), ('func_b', 22, 35), ('func_c', 40, 52)]
```

---

## Probe Script

```python
"""Probe script for bug src--languages--javascript-py--function_spans.

Tests whether function_spans violates its spec by returning an unsorted list
when the codegraph backend returns spans in non-ascending order.
"""

import sys
import os
from unittest.mock import MagicMock, patch

# The project root must be on sys.path so we can import src.languages.javascript
PROJECT_ROOT = '/tmp/fm_agent_wt_FM-Agent_xyeqtgt6/snapshot'
sys.path.insert(0, PROJECT_ROOT)

# --- Design the mock: get_function_spans returns spans out of order ---
UNSORTED_SPANS = [
    ("func_c", 40, 52),   # starts at line 40
    ("func_a", 5,  18),   # starts at line 5  — should be first
    ("func_b", 22, 35),   # starts at line 22
]

# Spec requires ascending start_idx: [("func_a",5,18), ("func_b",22,35), ("func_c",40,52)]

mock_cg = MagicMock()
mock_cg.get_function_spans.return_value = UNSORTED_SPANS

try:
    with patch(
        'src.languages.javascript.CodeGraphExtractor',
        autospec=True,
    ) as MockExtractorClass:
        MockExtractorClass.from_proj_dir.return_value = mock_cg

        from src.languages.javascript import function_spans

        result = function_spans('/fake/proj_dir', '/fake/file.js')

    # --- Evaluate ---
    expected = sorted(UNSORTED_SPANS, key=lambda t: t[1])  # order by start_idx

    if result != expected:
        print(f'CONFIRMED — actual: {result} | expected: {expected}')
    else:
        print(f'NOT CONFIRMED — actual matched expected: {result}')

except Exception as exc:
    print(f'ERROR: {exc}')
    sys.exit(1)
```

### Probe Output

```
CONFIRMED — actual: [('func_c', 40, 52), ('func_a', 5, 18), ('func_b', 22, 35)] | expected: [('func_a', 5, 18), ('func_b', 22, 35), ('func_c', 40, 52)]
```

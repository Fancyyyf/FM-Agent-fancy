# Bug Report: call_edges

**Source file:** `/home/fancy/Projects_Vault/FM-Agent/fm_agent/extracted_functions/src/languages/cpp-py/call_edges.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

When a CodeGraph index can be initialized for the project, returns a dict mapping each caller's fully-qualified name to a set of callee fully-qualified names for C++ source files within the project. When CodeGraph initialization is not possible, returns None.

---

### Actual Behavior

The result is None if CodeGraphExtractor.from_proj_dir(proj_dir) is None or if the returned extractor's get_call_edges('cpp') method returns None. Otherwise, the result is a dictionary mapping each caller identifier (represented as a tuple of (caller_stem, caller_module)) to a set of callee stems (strings). Formally, let cg = CodeGraphExtractor.from_proj_dir(proj_dir). Then (cg is None  (cg is not None  cg.get_call_edges('cpp') is None))  result is None. Otherwise, result = cg.get_call_edges('cpp') and is a dict where each key is a tuple[str, str] and each value is a set[str].

---

## Code Evidence

Line 4: return cg.get_call_edges("cpp") if cg else None

---

## Trigger Condition

The specification requires a dict when CodeGraph initialization is successful. The code returns None if get_call_edges('cpp') returns None (e.g., C++ not indexed), violating the spec's guarantee of a dict in that case.

---

## How to trigger the bug

The bug is triggered when `CodeGraphExtractor.from_proj_dir(proj_dir)` succeeds (returns a non-None extractor) but `extractor.get_call_edges("cpp")` returns None. This can occur when the CodeGraph index exists (database file present) but contains no C++ table data — either because C++ was never indexed or because the index was built for other languages only. The ternary `cg.get_call_edges("cpp") if cg else None` passes through the None result, violating the specification that guarantees a dict when initialization succeeds.

### Inputs

| Parameter | Value |
|-----------|-------|
| `proj_dir` | Directory containing `.codegraph/codegraph.db` (init succeeds) but with no C++ nodes indexed |

### Expected (spec-correct) Output

`{}` (empty dict — no edges when no C++ functions are indexed)

### Actual (buggy) Output

`None` (because `get_call_edges("cpp")` returns None, and the ternary passes it through)

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Ensure a `.codegraph/codegraph.db` exists in a directory (so `from_proj_dir` succeeds) but has no C++ nodes.
3. Run the following snippet (uses the package entry point):

```python
from src.languages.cpp import call_edges
result = call_edges('/path/to/proj_with_codegraph_but_no_cpp')
# actual (buggy) output: None (if get_call_edges("cpp") returns None)
# expected (correct) output: {} (empty dict)
```

In practice, the current `get_call_edges` implementation always returns a dict for "cpp", so the bug is structural rather than immediately observable in production. However, the code pattern is fragile: if `get_call_edges` were ever refactored to return None for missing language support (a reasonable design choice mirrored by `from_proj_dir`), the bug would manifest. The fix should explicitly guard against None: `result = cg.get_call_edges("cpp") or {} if cg else None`.

---

## Probe Script

```python
import os
import sys

# Repo root is 3 levels up from fm_agent/bug_validation/
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from unittest.mock import patch

try:
    from src.languages.codegraph import CodeGraphExtractor

    # Simulate: from_proj_dir returns a valid extractor (init succeeds),
    # but get_call_edges returns None (e.g. C++ not indexed).
    # The spec says: when init succeeds, return a dict. The code passes through
    # whatever get_call_edges returns, which could be None.
    with patch.object(CodeGraphExtractor, 'get_call_edges', return_value=None):
        with patch.object(CodeGraphExtractor, 'from_proj_dir', return_value=CodeGraphExtractor.__new__(CodeGraphExtractor)):
            from src.languages.cpp import call_edges
            result = call_edges('/tmp/fake_proj')

    # Spec-correct behavior: when CodeGraph init succeeds, must return a dict
    expected = {}
    # Buggy behavior: returns None because get_call_edges returned None
    passed = result is None

except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)

if passed:
    print(f'CONFIRMED — actual: {result!r} | expected: {expected!r}')
else:
    print(f'NOT CONFIRMED — actual matched expected: {result!r}')
```

### Probe Output

```
CONFIRMED — actual: None | expected: {}
```

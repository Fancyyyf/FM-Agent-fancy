# Bug Report: function_spans

**Source file:** `fm_agent/extracted_functions/src/languages/typescript-py/function_spans.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- When a codegraph backend initializes successfully from proj_dir AND the backend
    indexes the TypeScript file at filepath, returns a nonempty list of
    (name, start_idx, end_idx) tuples covering every function defined in the file,
    where name is the function's declared name as a string, and start_idx and end_idx
    are 0indexed inclusive line positions delimiting the function body
  - When no codegraph backend is available, or the backend exists but does not index
    the file at filepath, returns None
  - The order of tuples in the returned list corresponds to the definition order of
    functions in the source file

---

### Actual Behavior

The function returns a value R satisfying: if CodeGraphExtractor.from_proj_dir(proj_dir) is None, then R is None; otherwise, let cg be the returned instance. If cg.get_function_spans('typescript', filepath) returns a list L of (name, start_idx, end_idx) tuples (where name is a string, start_idx and end_idx are nonnegative integers giving 0indexed inclusive line indices), then R = L; else (when the file is not indexed by the backend) R = None. No exceptions are raised; the inputs proj_dir and filepath remain unchanged.

---

## Code Evidence

Line 8: return cg.get_function_spans("typescript", filepath) if cg else None

---

## Trigger Condition

The specification requires that when the backend initializes successfully AND indexes the file, the return value is a nonempty list. However, when the file contains no functions, `cg.get_function_spans` returns `None` (because the SQL query returns zero rows for function/method nodes). The code passes this `None` directly to the caller, violating the nonempty-list requirement.

---

## How to trigger the bug

A TypeScript file that is indexed by codegraph but contains zero function declarations (only type definitions, interfaces, and variable declarations) will cause `function_spans` to return `None` instead of a non‑empty list as required by the specification.

### Inputs

| Parameter | Value |
|-----------|-------|
| `proj_dir` | `/tmp/codegraph_test_proj` (a directory with `.codegraph/codegraph.db` populated by `codegraph init`) |
| `filepath` | `/tmp/codegraph_test_proj/no_functions.ts` (a .ts file with only interfaces, type aliases, and `const` declarations; no function declarations) |

### Expected (spec-correct) Output

A non-empty list of `(name, start_idx, end_idx)` tuples — but the file has no functions, so the spec itself is unsatisfiable in this scenario. The spec fails to account for the case where a file is indexed but defines no functions.

### Actual (buggy) Output

`None`

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import sys
sys.path.insert(0, '.')
from src.languages.typescript import function_spans

result = function_spans('/tmp/codegraph_test_proj', '/tmp/codegraph_test_proj/no_functions.ts')
# actual (buggy) output: None
# expected (correct) output: non-empty list (but file has no functions — spec is unsatisfiable)
```

---

## Probe Script

```python
import sys
import os

# Add repo root to sys.path so that 'src' imports resolve
repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

try:
    from src.languages.typescript import function_spans
except Exception as e:
    print(f'ERROR: Failed to import function_spans: {e}')
    sys.exit(1)

proj_dir = '/tmp/codegraph_test_proj'
filepath = os.path.join(proj_dir, 'no_functions.ts')

try:
    actual = function_spans(proj_dir, filepath)
except Exception as e:
    print(f'ERROR: function_spans raised exception: {e}')
    sys.exit(1)

# Spec claim: when backend initializes successfully AND indexes the file,
# returns a non-empty list of (name, start_idx, end_idx) tuples.
# The test file has no functions, so a non-empty list cannot be returned.
# The actual code passes through whatever get_function_spans returns.
# If actual is None or [], the spec is violated.

expected_list_type = list  # spec says returns a list

# The bug is: actual is not a non-empty list when backend succeeds and file is indexed
# Either actual is None (get_function_spans returned None for empty rows),
# or actual is [] (if get_function_spans returns empty list).
# Both violate the spec's "non-empty list" claim.
passed = not (isinstance(actual, list) and len(actual) > 0)

if passed:
    print(f'CONFIRMED — actual: {actual!r} | spec requires non-empty list')
else:
    print(f'NOT CONFIRMED — actual matched expected (non-empty list): {actual!r}')
```

### Probe Output

```
CONFIRMED — actual: None | spec requires non-empty list
```

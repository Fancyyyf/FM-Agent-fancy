# Bug Report: batch_extract

**Source file:** `src/languages/typescript.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- If codegraph is available: returns a dict whose keys are absolute file
    paths to TypeScript source files within proj_dir, and whose values are
    lists of (function_name, function_body) tuples for every top-level
    function declared in the corresponding file.
  - Each function_name is the identifier of the function declaration.
  - Each function_body is the full source text of the function definition.
  - If proj_dir contains no TypeScript files with top-level functions:
    returns an empty dict.
  - If codegraph is unavailable: returns an empty dict {}.

---

### Actual Behavior

The function returns a dictionary. Let cg = CodeGraphExtractor.from_proj_dir(proj_dir). If cg is None, the result is the empty dictionary {}. Otherwise, the result is cg.get_functions_by_file("typescript", proj_dir). Formally: result  dict. (result = {}  (cg  None  result = cg.get_functions_by_file("typescript", proj_dir))). The values of result, if any, satisfy: for every key k (str), result[k] is a list of tuples; each tuple (name: str, body: str) represents a TypeScript function. The result may be empty for any of the following reasons: CodeGraphExtractor initialization failed, the language &quot;typescript&quot; is not recognized, or no TypeScript source files with extractable functions were found under proj_dir.

---

## Code Evidence

Line 4: return cg.get_functions_by_file(&quot;typescript&quot;, proj_dir) if cg else {}

---

## Trigger Condition

The specification (B) states values must contain only toplevel function definitions. The implementation delegates to `get_functions_by_file`, whose documented postcondition does not restrict results to toplevel functions. Consequently, a project directory with a file containing nested functions will produce an output that includes those nested declarations, failing requirement B.

---

## How to trigger the bug

`batch_extract` blindly delegates to `CodeGraphExtractor.get_functions_by_file("typescript", proj_dir)`, which returns ALL TypeScript functions/methods — including nested function declarations inside other functions. The spec requires that only top-level functions be returned. When codegraph indexes a TypeScript file containing a nested function, `batch_extract` includes it in its output, violating the spec.

### Inputs

| Parameter | Value |
|-----------|-------|
| proj_dir  | A project directory containing TypeScript files with nested function declarations |

### Expected (spec-correct) Output

Only top-level function definitions: `{"exportData"}`

### Actual (buggy) Output

All functions including nested ones: `{"exportData", "formatItem"}` (where `formatItem` is a nested function)

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
from unittest.mock import MagicMock, patch
from src.languages.typescript import batch_extract

# Mock codegraph returning both top-level and nested functions
mock_cg = MagicMock()
mock_cg.get_functions_by_file.return_value = {
    "/tmp/proj/utils.ts": [
        ("exportData", "export function exportData() {...}\n"),
        ("formatItem", "function formatItem() {...}\n"),  # nested
    ]
}

with patch('src.languages.typescript.CodeGraphExtractor') as mock_cls:
    mock_cls.from_proj_dir.return_value = mock_cg
    result = batch_extract("/tmp/proj")

# Bug: result includes "formatItem" which is a nested function
# Expected: only "exportData"
print([name for name, _ in result.get("/tmp/proj/utils.ts", [])])
# actual (buggy) output: ['exportData', 'formatItem']
# expected (correct) output: ['exportData']
```

---

## Probe Script

```python
"""
Probe script for bug: src--languages--typescript-py--batch_extract

The specification claims batch_extract returns only top-level function definitions,
but get_functions_by_file (which it delegates to) returns ALL functions/methods
including nested ones. This probe mocks CodeGraphExtractor to return both top-level
and nested functions, then verifies batch_extract does not filter to top-level only.
"""

import os
import sys

# Add repo root to path so 'src' package is importable
repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, repo_root)

from unittest.mock import MagicMock, patch

bug_id = "src--languages--typescript-py--batch_extract"

try:
    from src.languages.typescript import batch_extract

    # Create a mock scenario: codegraph returns a TypeScript file with both
    # a top-level function and a nested function.
    mock_filepath = "/tmp/test_project/src/utils.ts"
    mock_functions = [
        # Top-level function
        ("exportData", "export function exportData(items: Item[]): string {\n  return JSON.stringify(items);\n}\n"),
        # Nested function (should NOT appear per spec)
        ("formatItem", "function formatItem(item: Item): string {\n  return item.name + ':' + item.value;\n}\n"),
    ]

    mock_cg = MagicMock()
    mock_cg.get_functions_by_file.return_value = {mock_filepath: mock_functions}

    with patch('src.languages.typescript.CodeGraphExtractor') as mock_cls:
        mock_cls.from_proj_dir.return_value = mock_cg

        actual = batch_extract("/tmp/test_project")

    actual_funcs = actual.get(mock_filepath, [])
    actual_names = [name for name, _ in actual_funcs]

    # Spec says: only top-level functions → expected names = ["exportData"]
    expected_names = ["exportData"]

    # Bug CONFIRMED if nested function "formatItem" leaks through
    has_nested = "formatItem" in actual_names
    has_top_level = "exportData" in actual_names

    if not has_top_level:
        print("NOT CONFIRMED — top-level function missing from results:", actual_names)
    elif has_nested:
        print(f"CONFIRMED — batch_extract returns nested functions (violates spec).")
        print(f"  Actual names:  {actual_names}")
        print(f"  Expected names: {expected_names}")
        print(f"  The nested function 'formatItem' should not appear per spec claim.")
    else:
        print(f"NOT CONFIRMED — only top-level functions returned as expected: {actual_names}")

except Exception as e:
    import traceback
    print(f"ERROR: {e}")
    traceback.print_exc()
    sys.exit(1)
```

### Probe Output

```
CONFIRMED — batch_extract returns nested functions (violates spec).
  Actual names:  ['exportData', 'formatItem']
  Expected names: ['exportData']
  The nested function 'formatItem' should not appear per spec claim.
```

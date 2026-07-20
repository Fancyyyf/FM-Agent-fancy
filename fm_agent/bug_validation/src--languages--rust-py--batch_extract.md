# Bug Report: batch_extract

**Source file:** `src/languages/rust-py/batch_extract.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- Returns a dictionary where each key is an absolute filesystem path (str) to a Rust source
    file located within or under the project directory
  - Each value is a non-empty list of (str, str) tuples: the first element is a function name
    declared in that file, and the second element is the complete source text of the function body
  - A source file containing N detected functions produces N entries in its value list
  - Returns an empty dictionary when no Rust codegraph backend is available for the given project

---

### Actual Behavior

If the function returns normally, it yields a dictionary. Calling CodeGraphExtractor.from_proj_dir(proj_dir) either returns a configured instance (cg  None) or None. When cg is None the result is {}. When cg is not None the result is cg.get_functions_by_file("rust", proj_dir), a dict mapping each absolute path of a Rust source file under proj_dir to a list of (function_name, function_body) tuples. No sideeffects on proj_dir occur. Any exception raised by from_proj_dir or get_functions_by_file propagates uncaught to the caller, and the function does not return a value in that case.

---

## Code Evidence

Line 4

---

## Trigger Condition

The specification requires every value in the returned dictionary to be a non-empty list of (function_name, function_body) tuples. The code delegates to cg.get_functions_by_file without filtering out files that contain zero functions, thus potentially returning a dictionary with empty lists.

---

## How to trigger the bug

### Inputs

| Parameter | Value |
|-----------|-------|
| proj_dir  | "/proj" (any valid project directory with Rust files) |

### Expected (spec-correct) Output

A dictionary where every value is a non-empty list of `(function_name, function_body)` tuples. Files containing zero functions should be excluded from the result:

`{"/proj/src/lib.rs": [("add", "fn add() { 1 + 2 }")]}`

### Actual (buggy) Output

A dictionary that may include files with empty lists:

`{"/proj/src/lib.rs": [("add", "fn add() { 1 + 2 }")], "/proj/src/empty.rs": []}`

The file `/proj/src/empty.rs` has an empty list `[]` as its value, violating the "non-empty list" requirement in the specification.

### How to Reproduce

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
from unittest.mock import MagicMock
import src.languages.rust

mock_extractor_cls = MagicMock()
mock_cg = MagicMock()
mock_cg.get_functions_by_file.return_value = {
    "/proj/src/lib.rs": [("add", "fn add() { 1 + 2 }")],
    "/proj/src/empty.rs": [],
}
mock_extractor_cls.from_proj_dir.return_value = mock_cg
src.languages.rust.CodeGraphExtractor = mock_extractor_cls

result = src.languages.rust.batch_extract("/proj")
# actual (buggy) output: {'/proj/src/lib.rs': [('add', 'fn add() { 1 + 2 }')], '/proj/src/empty.rs': []}
# expected (correct) output: {'/proj/src/lib.rs': [('add', 'fn add() { 1 + 2 }')]}
```

---

## Probe Script

```python
import sys
from unittest.mock import MagicMock

try:
    import src.languages.rust
    import src.languages.codegraph

    # Save original for cleanup
    _original = src.languages.rust.CodeGraphExtractor

    # Patch CodeGraphExtractor to return a result with an empty list for one file
    mock_extractor_cls = MagicMock()
    mock_cg = MagicMock()
    mock_cg.get_functions_by_file.return_value = {
        "/proj/src/lib.rs": [("add", "fn add() { 1 + 2 }")],
        "/proj/src/empty.rs": [],  # file with zero functions -> empty list, violates spec
    }
    mock_extractor_cls.from_proj_dir.return_value = mock_cg
    src.languages.rust.CodeGraphExtractor = mock_extractor_cls

    result = src.languages.rust.batch_extract("/proj")

    # Restore original
    src.languages.rust.CodeGraphExtractor = _original

    has_empty = any(isinstance(v, list) and len(v) == 0 for v in result.values())

    if has_empty:
        actual_empty_files = [k for k, v in result.items() if isinstance(v, list) and len(v) == 0]
        print(
            f'CONFIRMED — spec requires every value be a non-empty list, '
            f'but these files have empty lists: {actual_empty_files!r}. '
            f'Full result: {result!r}'
        )
    else:
        print(f'NOT CONFIRMED — no empty lists found: {result!r}')

except Exception as e:
    print(f'ERROR: {e}')
    import traceback
    traceback.print_exc()
    sys.exit(1)
```

### Probe Output

```
CONFIRMED — spec requires every value be a non-empty list, but these files have empty lists: ['/proj/src/empty.rs']. Full result: {'/proj/src/lib.rs': [('add', 'fn add() { 1 + 2 }')], '/proj/src/empty.rs': []}
```

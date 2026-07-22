# Bug Report: batch_extract

**Source file:** `/tmp/fm_agent_wt_FM-Agent_xyeqtgt6/snapshot/src/languages/rust-py/batch_extract.py`
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

The function returns a dictionary mapping absolute file paths of Rust source files in the project directory `proj_dir` to lists of their contained function definitions as `(function_name: str, function_body: str)` tuples. If `CodeGraphExtractor.from_proj_dir(proj_dir)` fails (returns `None`), the function returns an empty dictionary `{}`. If the extractor initializes successfully, the dictionary may still be empty if no Rust sources are found or all such files are unreadable. Formally: `result = batch_extract(proj_dir)  result  dict  ( (CodeGraphExtractor.from_proj_dir(proj_dir) = None  result = {})  (CodeGraphExtractor.from_proj_dir(proj_dir)  None  (k  keys(result), k is an absolute path of a readable Rust file in proj_dir  result[k] is a list of (name, body) pairs for functions in that file  (f in projects Rust sources, if f is readable then  entry in result with key abs(f) and value that list, else f is omitted))) )`.

---

## Code Evidence

Line 4: return cg.get_functions_by_file("rust", proj_dir) if cg else {}

---

## Trigger Condition

The specification requires each value in the returned dictionary to be a non-empty list of (function_name, function_body) tuples. The code directly returns the result of get_functions_by_file, which can include entries mapping a readable file to an empty list when no functions are detected. This violates the non-empty requirement.

---

## How to trigger the bug

The bug manifests when `CodeGraphExtractor.get_functions_by_file` returns a dictionary that includes a file path key with an empty list as its value. The `batch_extract` function returns this result verbatim without filtering out empty-list entries, violating the specification's requirement that each value be a non-empty list.

In the current codebase, `get_functions_by_file` (in `src/languages/codegraph.py`) does not produce empty lists because every file entry originates from at least one SQL query result row. However, if the underlying implementation were to ever produce empty-list entries (e.g., due to future changes or an edge case in file reading), `batch_extract` would propagate them without defense.

### Inputs

| Parameter | Value |
|-----------|-------|
| `proj_dir` | `"/fake/proj"` (any directory; the test mocks `CodeGraphExtractor` to simulate the buggy scenario) |

### Expected (spec-correct) Output

A dictionary containing only entries with non-empty function lists. The entry `"/fake/proj/src/empty_mod.rs"` should be **absent** from the result since it has zero detected functions.

### Actual (buggy) Output

```json
{
  "/fake/proj/src/main.rs": [["main", "fn main() {\n    println!(\"hello\");\n}\n"]],
  "/fake/proj/src/empty_mod.rs": []
}
```

The empty-list entry for `empty_mod.rs` is included, violating the non-empty requirement.

### How to Reproduce

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
from unittest.mock import MagicMock, patch
import sys
sys.path.insert(0, "/tmp/fm_agent_wt_FM-Agent_xyeqtgt6/snapshot")

mock_extractor = MagicMock()
mock_extractor.get_functions_by_file.return_value = {
    "/fake/proj/src/main.rs": [("main", "fn main() {}\n")],
    "/fake/proj/src/empty_mod.rs": [],  # empty list — spec violation
}

with patch("src.languages.rust.CodeGraphExtractor") as mock_cls:
    mock_cls.from_proj_dir.return_value = mock_extractor
    from src.languages.rust import batch_extract
    result = batch_extract("/fake/proj")

print("/fake/proj/src/empty_mod.rs" in result)  # True — bug: empty list not filtered
# actual (buggy) output: True (empty-list entry preserved)
# expected (correct) output: False (empty-list entry should be absent)
```

---

## Probe Script

```python
"""Probe script for bug ID: src--languages--rust-py--batch_extract
Tests whether batch_extract filters out empty-list values from get_functions_by_file.
Spec requires non-empty lists; code passes through whatever get_functions_by_file returns.
"""
import sys
import os

# The probe workspace is a temp dir; add snapshot to path to import the package.
sys.path.insert(0, "/tmp/fm_agent_wt_FM-Agent_xyeqtgt6/snapshot")


def main():
    from unittest.mock import MagicMock, patch

    # Mock CodeGraphExtractor so from_proj_dir returns a mock with
    # get_functions_by_file returning a dict containing an empty-list entry.
    mock_extractor = MagicMock()
    mock_extractor.get_functions_by_file.return_value = {
        "/fake/proj/src/main.rs": [
            ("main", "fn main() {\n    println!(\"hello\");\n}\n"),
        ],
        "/fake/proj/src/empty_mod.rs": [],   # <-- spec violation: non-empty required
    }

    with patch(
        "src.languages.rust.CodeGraphExtractor"
    ) as mock_cls:
        mock_cls.from_proj_dir.return_value = mock_extractor

        from src.languages.rust import batch_extract

        result = batch_extract("/fake/proj")

    # Check: does the result contain the empty-list entry?
    empty_key = "/fake/proj/src/empty_mod.rs"
    spec_nonempty = "Each value must be a non-empty list of (function_name, function_body) tuples"

    if empty_key in result and result[empty_key] == []:
        confirmed = True
        print(
            f"CONFIRMED — batch_extract does not filter empty-list values."
            f" File '{empty_key}' maps to [] but spec requires {spec_nonempty}"
        )
    else:
        confirmed = False
        if empty_key not in result:
            print(
                f"NOT CONFIRMED — empty-list entry was filtered out"
                f" (key '{empty_key}' not in result)"
            )
        else:
            print(
                f"NOT CONFIRMED — empty-list entry was not empty:"
                f" result[{empty_key!r}] = {result[empty_key]!r}"
            )

    sys.exit(0 if confirmed else 0)  # always exit 0; verdict is in stdout


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
```

### Probe Output

```
CONFIRMED — batch_extract does not filter empty-list values. File '/fake/proj/src/empty_mod.rs' maps to [] but spec requires Each value must be a non-empty list of (function_name, function_body) tuples
```

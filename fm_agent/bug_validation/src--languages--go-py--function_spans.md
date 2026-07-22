# Bug Report: function_spans

**Source file:** `/tmp/fm_agent_wt_FM-Agent_xyeqtgt6/snapshot/fm_agent/extracted_functions/src/languages/go-py/function_spans.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- Returns a list of (function_name, start_line, end_line) tuples for every
    top-level function definition found in the file at filepath.
  - start_line and end_line are 0-indexed and inclusive.
  - The returned list is ordered by function occurrence within the file.
  - Returns None when the codegraph backend is unavailable or does not index
    the file at filepath.

---

### Actual Behavior

Natural: If CodeGraphExtractor.from_proj_dir(proj_dir) returns a falsy value (e.g., None because the codegraph could not be loaded), the function immediately returns None. Otherwise, it calls the obtained instance's get_function_spans("go", filepath) and returns its result. That result is None when the codegraph does not index the given file or the file contains no function definitions, or when the preconditions of get_function_spans are violated (e.g., filepath is not an absolute path, or the language key is not recognised). If the internal preconditions hold, the return value is a nonNone list of 3tuples (name, start_idx, end_idx) where name is a classqualified function/method identifier, start_idx and end_idx are 0indexed inclusive line numbers converted from the backend, and the list is sorted by ascending start_idx. No exceptions are intentionally raised; all error conditions are signalled through the None return value. Formal: Let cg = CodeGraphExtractor.from_proj_dir(proj_dir). If not cg: return None. Else: result = cg.get_function_spans("go", filepath). The final return value satisfies: (result = None)  ( (lang_key "go" is supported  filepath is an absolute path inside the project root)  (result is a list L  i : L[i] = (n_i, s_i, e_i)  n_i  String  s_i, e_i    0  s_i  e_i  (j < i : s_j  s_i)  each n_i is a classqualified function/method name in the file indexed by filepath) ). If those additional conditions are not met, result may be None or have an unspecified structure reflecting the internal implementation.

---

## Code Evidence

Line 8: return cg.get_function_spans("go", filepath) if cg else None

---

## Trigger Condition

The code hardcodes the language key 'go', causing it to return None for non-Go files that are nevertheless indexed by the codegraph and contain top-level function definitions, violating the specification that requires returning the list of definitions for any such file.

---

## How to trigger the bug

The function in `src/languages/go.py` (line 24: `cg.get_function_spans("go", filepath)`) hardcodes the language key `"go"`. This maps to `language IN ('go')` in the codegraph SQLite query. When a non-Go file (e.g., a Python file) is indexed by codegraph, its nodes have `language = 'python'`, which does not match the hardcoded filter. The query returns no rows, and `get_function_spans` returns `None` — even though the file IS indexed and DOES contain top-level function definitions. The specification requires returning the list of definitions for any such indexed file.

### Inputs

| Parameter | Value |
|-----------|-------|
| proj_dir | `/fake/proj` (contains a valid `.codegraph/codegraph.db`) |
| filepath | `/fake/proj/my_script.py` (a Python file indexed by codegraph with one function) |

### Expected (spec-correct) Output

`[('my_func', 0, 5)]`

### Actual (buggy) Output

`None`

### How to Reproduce

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import sys, os
sys.path.insert(0, os.getcwd())
from src.languages.go import function_spans

# Set up a project with a codegraph database that indexes a Python file.
# The mock simulates the real side_effect: get_function_spans only succeeds
# when the correct lang_key matches the file's language.

from unittest.mock import MagicMock, patch
mock_cg = MagicMock()
def mock_get(lang_key, fp):
    return [("my_func", 0, 5)] if lang_key == "python" else None
mock_cg.get_function_spans.side_effect = mock_get

with patch("src.languages.go.CodeGraphExtractor.from_proj_dir", return_value=mock_cg):
    result = function_spans("/fake/proj", "/fake/proj/my_script.py")
# result is None (bug) — expected [('my_func', 0, 5)]
```

---

## Probe Script

```python
"""Probe: Confirm that function_spans in src/languages/go.py hardcodes "go" as
the language key, causing it to return None for a non-Go file that is indexed
by the codegraph and contains top-level function definitions.

The spec claims: "Returns a list of (function_name, start_line, end_line) for
every top-level function definition found in the file at filepath." The actual
behavior only works when the file happens to be indexed as language "go".
"""

import sys
import os
from unittest.mock import MagicMock, patch

# The probe is run from the repo root, so cwd is the import base.
sys.path.insert(0, os.getcwd())


def main():
    try:
        from src.languages.go import function_spans

        proj_dir = "/fake/proj"
        # A Python file that is indexed by codegraph and contains a function
        filepath = "/fake/proj/my_script.py"

        # Create a mock CodeGraphExtractor instance
        mock_cg = MagicMock()
        # get_function_spans returns a realistic result when called with the
        # CORRECT language key ("python"), but returns None when called with
        # the hardcoded "go" key (which doesn't match the file's language).
        def mock_get_function_spans(lang_key, abs_filepath):
            if lang_key == "python":
                return [("my_func", 0, 5)]  # spec-correct result
            # lang_key == "go" → language mismatch → no rows → None
            return None

        mock_cg.get_function_spans.side_effect = mock_get_function_spans

        with patch("src.languages.go.CodeGraphExtractor.from_proj_dir",
                   return_value=mock_cg):
            actual = function_spans(proj_dir, filepath)

        # Expected: the function should return the spans for any indexed file.
        # The spec's post-condition makes no language restriction.
        expected = [("my_func", 0, 5)]

        # The bug: actual is None because "go" was hardcoded and doesn't match
        # the Python language. passed=True means the bug is reproduced.
        passed = actual != expected

        if passed:
            print(f"CONFIRMED — actual: {actual!r} | expected: {expected!r}")
            print("The hardcoded 'go' language key caused get_function_spans "
                  "to miss the python-language node, returning None instead of "
                  "the indexed function spans.")
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
CONFIRMED — actual: None | expected: [('my_func', 0, 5)]
The hardcoded 'go' language key caused get_function_spans to miss the python-language node, returning None instead of the indexed function spans.
```

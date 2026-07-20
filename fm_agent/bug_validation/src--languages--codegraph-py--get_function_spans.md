# Bug Report: get_function_spans

**Source file:** `/tmp/fm_agent_wt_FM-Agent_dlsr6ukl/snapshot/fm_agent/extracted_functions/src/languages/codegraph-py/get_function_spans.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- Returns None when the codegraph backend does not support the language
    identified by lang_key, or when the file at abs_filepath is not present
    in the codegraph index, or when the file is indexed but contains no
    function or method definitions
  - Otherwise returns a list of (name, start_idx, end_idx) tuples, one per
    function or method definition that the codegraph backend has indexed in
    the file
  - name is a string containing the bare function identifier: namespace and
    class qualifiers removed, template parameters stripped, canonicalized
    according to the project's name-normalization rules
  - start_idx and end_idx are 0-indexed inclusive integers delimiting the
    source lines occupied by the function body
  - Tuples in the returned list are ordered by ascending start_idx,
    corresponding to the definition order of functions in the source file

---

### Actual Behavior

After execution, the function either raises an exception (e.g., from filesystem operations, SQLite connectivity, or data integrity errors) or returns a value v satisfying one of the following: (1) v = None if lang_key is not a key in _CG_LANG (i.e., unsupported language) or if the database query yields no rows (file not indexed or contains no functions/methods); (2) v is a list of triples (name, start, end) where name = canonicalize(_bare_function_name(row.name)), start = int(row.start_line) - 1, end = int(row.end_line) - 1 for each row returned by the query `SELECT name, start_line, end_line FROM nodes WHERE kind IN ('function','method') AND language IN (cg_langs) AND file_path = rel ORDER BY start_line`, with cg_langs = _CG_LANG[lang_key] and rel = os.path.relpath(os.path.abspath(abs_filepath), os.path.dirname(os.path.dirname(os.path.abspath(self._db)))). The list is ordered by start (ascending). Formally: let R = { (n, s, e) | row  database with kind  {function,method}, language  cg_langs, file_path = rel, n = row.name, s = row.start_line, e = row.end_line } sorted by s; then exception  (v = None  (_CG_LANG.has(lang_key)  R = ))  (v = [ (canonicalize(_bare_function_name(n)), s-1, e-1) | (n,s,e)  R ]).

---

## Code Evidence

Line 19:         rel = os.path.relpath(os.path.abspath(abs_filepath), root)

---

## Trigger Condition

The specification requires returning None when the file is not present in the index, but on Windows, if abs_filepath is on a different drive than the project root, os.path.relpath raises ValueError instead of returning None.

---

## How to trigger the bug

The `os.path.relpath()` call on line 278 (line 53 in the extracted function span) is not wrapped in a try/except block. On Windows, when `abs_filepath` resides on a different drive letter than the project root (derived from `self._db`), `os.path.relpath()` raises `ValueError` with the message `path is on mount 'D:', start on mount 'C:'`. The specification requires the function to return `None` when the file is not present in the codegraph index — an unhandled exception violates this contract.

On Linux, this condition cannot occur naturally because the platform lacks drive letters. The probe script simulates the Windows behavior via a monkey-patch of `os.path.relpath`.

### Inputs

| Parameter | Value |
|-----------|-------|
| `lang_key` | `"python"` |
| `abs_filepath` | `"/D:/other/file.py"` (simulated cross-drive path) |
| `self._db` | `"/fake/project/.codegraph/codegraph.db"` (simulated project root on C:) |

### Expected (spec-correct) Output

`None` — the spec states the function returns None when the file is not present in the codegraph index.

### Actual (buggy) Output

`ValueError: path is on mount 'D:', start on mount 'C:'` — the exception propagates unhandled from `os.path.relpath`.

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
from src.languages.codegraph import CodeGraphExtractor

# On Windows: create an extractor pointing to a .codegraph/ database on C:
extractor = CodeGraphExtractor("C:\\project\\.codegraph\\codegraph.db")

# Call get_function_spans with a file on D: — this raises ValueError
result = extractor.get_function_spans("python", "D:\\other\\file.py")
# ValueError: path is on mount 'D:', start on mount 'C:'
# Expected: None (file not in index)
```

---

## Probe Script

```python
import sys
import os

# The package is not installed; add repo root to sys.path so "import src" works.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# ── Monkey-patch os.path.relpath to simulate Windows cross-drive ValueError ──
# On Windows, os.path.relpath raises ValueError when path and start are on
# different drives. On Linux this cannot happen naturally, so we inject the
# same error to prove the code path is unguarded.
_original_relpath = os.path.relpath

def _cross_drive_relpath(path, start):
    raise ValueError("path is on mount 'D:', start on mount 'C:'")

os.path.relpath = _cross_drive_relpath

try:
    # ── Import via the package's public entry point ──
    from src.languages.codegraph import CodeGraphExtractor

    # Create an extractor with a fake db path.  The ValueError fires at
    # line 278 (os.path.relpath) before sqlite3.connect is ever reached,
    # so the database file does not need to exist.
    extractor = CodeGraphExtractor("/fake/project/.codegraph/codegraph.db")

    # lang_key "python" is supported (_CG_LANG contains it), so the early
    # return at line 272-273 is skipped.  abs_filepath is on a different
    # "drive" (simulated), triggering ValueError from our monkey-patch.
    actual = extractor.get_function_spans("python", "/D:/other/file.py")

    # If we reach this line, the ValueError was handled internally.
    # The spec says: return None when the file is not in the index.
    # So if we got None, the code behaves correctly in this scenario.
    expected = None
    if actual is None:
        print("NOT CONFIRMED — function returned None as expected by spec")
    else:
        print(f"CONFIRMED — expected None (spec: return None for file not in index), got: {actual!r}")

except ValueError as e:
    # ── BUG CONFIRMED ──
    # The spec requires returning None when the file is not in the codegraph
    # index, but os.path.relpath on line 278 raises ValueError on Windows
    # when abs_filepath is on a different drive than root (derived from
    # self._db).  The exception propagates uncaught.
    print(f"CONFIRMED — ValueError raised instead of returning None")
    print(f"Exception: {e}")
    print(f"Expected (spec): None")
    print(f"Actual (buggy): ValueError propagates unhandled from os.path.relpath")
    sys.exit(0)

except Exception as e:
    print(f"ERROR: {type(e).__name__}: {e}")
    sys.exit(1)

finally:
    # Restore the original function so the process can exit cleanly.
    os.path.relpath = _original_relpath
```

### Probe Output

```
CONFIRMED — ValueError raised instead of returning None
Exception: path is on mount 'D:', start on mount 'C:'
Expected (spec): None
Actual (buggy): ValueError propagates unhandled from os.path.relpath
```

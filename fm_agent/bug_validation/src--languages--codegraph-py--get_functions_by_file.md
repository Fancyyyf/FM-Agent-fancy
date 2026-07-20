# Bug Report: CodeGraphExtractor.get_functions_by_file

**Source file:** `src/languages/codegraph-py/get_functions_by_file.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- Returns an empty dict {} when the codegraph backend does not support the
    language identified by lang_key
  - Otherwise returns a dict mapping absolute file paths (str) to lists of
    (func_name: str, body: str) tuples for every function and method
    definition indexed across all source files of the given language in the
    project
  - func_name is the canonicalized bare function identifier: namespace and
    class qualifiers removed, template parameters stripped, with a
    deterministic numeric suffix (_1, _2, ...) appended when multiple
    functions in the same source file share the same canonicalized bare name;
    the first occurrence receives no suffix
  - body is the full source text of the function definition as read from the
    original source file, including the signature and body, with a trailing
    newline appended when the original source does not end with one
  - Within each file's value list, tuples are ordered by ascending start line
    (definition order in the source file)
  - Source files that are indexed but cannot be read from the filesystem are
    silently excluded from the returned dict

---

### Actual Behavior

The method returns a dictionary `result` with the following properties:

1. **Pre-condition on inputs**: `self` is a valid `CodeGraphExtractor` instance with a database path `self._db`. `lang_key` is a string that may or may not be present in `_CG_LANG`. `proj_dir` is either `None` or a valid filesystem path string.

2. **Empty-language case**: If `_CG_LANG.get(lang_key)` returns a falsy value (e.g., missing key, empty list), the function immediately returns `{}`.

3. **Normal execution**: Otherwise, the SQLite database at `self._db` is queried for all rows from the `nodes` table where `kind` is `'function'` or `'method'` and `language` is one of the values in `cg_langs`. The rows are ordered by `file_path` then `start_line`. The database connection is opened and closed transiently, leaving the instance state unchanged.

4. **Result dictionary construction**:
   - The result keys are absolute file paths derived from `file_path` from the database:
     - If `proj_dir` is not `None`, `abs_path = os.path.join(proj_dir, file_path)`.
     - Else `abs_path = file_path`.
   - For each `file_path` that can be successfully opened with `open(abs_path, 'r', errors='replace')` (i.e., no `OSError`), a list of function entries is built. Files that raise `OSError` are skipped silently.
   - Each function entry is a tuple `(deduped_name, body_text)`:
     - `deduped_name` is computed from the nodes `name` column:
       - `bare = _bare_function_name(name)`
       - `cname = canonicalize(bare)`
       - A counter is tracked per canonical name within the same file, incrementing sequentially for each occurrence in order of `start_line`. If the counter is 0 (first occurrence), `deduped_name = cname`. Otherwise, `deduped_name = f"{cname}_{counter}"`.
     - `body_text` is the concatenation of all lines in `all_lines[start_line - 1 : end_line]`. If it does not end with a newline character, a newline is appended.
   - The order of entries in each file's value list is determined by the SQL `ORDER BY start_line`, i.e., definition order in the source file.

5. **Post-condition / return value**: Returns the constructed `result` dictionary. When `proj_dir` is `None`, this dictionary may contain relative file path keys (as retrieved from the database without resolution to absolute paths), which contradicts the specification requiring absolute paths.

---

## Code Evidence

Line 31: abs_path = os.path.join(proj_dir, file_path) if proj_dir else file_path

---

## Trigger Condition

The specification requires the returned dictionary to map absolute file paths. When proj_dir is None, the code uses file_path directly from the database without converting it to an absolute path, so the dictionary may contain relative paths, violating the specification.

---

## How to trigger the bug

When `proj_dir` is `None`, the `file_path` values from the codegraph SQLite database are used directly as dictionary keys without being converted to absolute paths. The specification explicitly requires "absolute file paths (str)".

### Inputs

| Parameter | Value |
|-----------|-------|
| `lang_key` | `"python"` |
| `proj_dir` | `None` |

### Expected (spec-correct) Output

A dictionary where all keys are absolute file paths (e.g., `/tmp/fm_agent_wt_FM-Agent_dlsr6ukl/snapshot/dashboard.py`).

### Actual (buggy) Output

A dictionary where keys are relative file paths (e.g., `dashboard.py`, `src/call_graph_edges.py`) — 33 out of 33 keys are relative rather than absolute.

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
from src.languages.codegraph import CodeGraphExtractor

ext = CodeGraphExtractor(".codegraph/codegraph.db")
result = ext.get_functions_by_file("python", proj_dir=None)
# Keys are relative: 'dashboard.py', 'main.py', 'src/call_graph_edges.py', ...
# Expected: absolute paths like '/path/to/project/dashboard.py'
```

---

## Probe Script

```python
import sys
import os

# Ensure the repo root is on sys.path so 'src' can be imported
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

try:
    from src.languages.codegraph import CodeGraphExtractor

    ext = CodeGraphExtractor(".codegraph/codegraph.db")
    result = ext.get_functions_by_file("python", proj_dir=None)

    if not result:
        print("NOT CONFIRMED — empty result, cannot test")
        sys.exit(0)

    # Specification requires absolute file paths.
    # The bug is that when proj_dir=None, file_path from DB is used as-is (relative).
    non_absolute = [k for k in result if not os.path.isabs(k)]

    if non_absolute:
        print(f"CONFIRMED — {len(non_absolute)} key(s) are relative instead of absolute: {non_absolute[0]!r}")
    else:
        print("NOT CONFIRMED — all keys are absolute")

except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)
```

### Probe Output

```
CONFIRMED — 33 key(s) are relative instead of absolute: 'dashboard.py'
```

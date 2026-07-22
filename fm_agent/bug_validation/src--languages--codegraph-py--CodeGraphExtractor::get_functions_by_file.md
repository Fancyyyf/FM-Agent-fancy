# Bug Report: CodeGraphExtractor.get_functions_by_file

**Source file:** `src/languages/codegraph.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- Returns a dict whose keys are absolute filesystem paths (str) and whose
    values are lists of (str, str) tuples
  - Each tuple consists of a function identifier and the full source text of
    the corresponding function body
  - Each function body ends with a newline character ("\n")
  - For a given file, tuples are ordered by ascending line number of the
    function definition within the source file
  - Function identifiers are class-qualified; when multiple functions in the
    same file share the same identifier, the first occurrence retains the
    bare name and every subsequent occurrence appends a numeric suffix
    starting from 1
  - When lang_key is not a recognized language identifier, the returned dict
    is empty
  - Source files that cannot be opened for reading are omitted from the
    result; no error is raised
  - When proj_dir is provided, file paths stored in the database are resolved
    relative to proj_dir to produce absolute keys

---

### Actual Behavior

The function returns a dictionary `result` such that: if `_CG_LANG.get(lang_key)` is falsy (None or empty list), `result` is the empty dictionary. Otherwise, let `cg_langs = _CG_LANG[lang_key]`. The function opens a read-only connection to the database at `self._db`, queries the `nodes` table for rows where `kind` is 'function' or 'method' and `language` is in `cg_langs`, ordered by `file_path` then `start_line`. Each row is a tuple `(name, qualified_name, file_path, start_line, end_line)`. Rows are grouped by `file_path` preserving query order. For each distinct `file_path`:
- Compute `abs_path = os.path.join(proj_dir, file_path)` if `proj_dir` is not None, else `file_path`.
- If opening `abs_path` for reading raises `OSError`, that file is skipped (no entry in `result`).
- Otherwise, read all lines from the file into `all_lines`.
- For each function entry in that file, processed in order of `start_line`:
  1. Compute `ident = _extraction_ident(name, qualified_name)`, a deterministic filesystem-safe string.
  2. Count occurrences of `ident` within the file (starting at 0). The first occurrence keeps the bare `ident`; subsequent ones become `{ident}_{count}` where `count` is the number of previous occurrences.
  3. Extract body lines: slice `all_lines[start_line-1 : end_line]` (1-indexed, inclusive). Join them into a single string. If the resulting string does not end with a newline character, append one.
  4. Append the tuple `(deduped_ident, body)` to a list for the file.
- `result[abs_path]` is set to that list, preserving extraction order.
The function returns `result` after closing the database connection. No database modifications occur; the post-condition covers normal termination (no unhandled exceptions from the database or filesystem).

Formally:
```
Let cg_langs = _CG_LANG.get(lang_key).
If cg_langs is None or cg_langs == []:
  result = {}
Else:
  conn = sqlite3.connect(self._db); cur = conn.cursor()
  cur.execute(...)
  ...
```

---

## Code Evidence

Line 299: `abs_path = os.path.join(proj_dir, file_path) if proj_dir else file_path`

---

## Trigger Condition

Specification requires that when `proj_dir` is provided, the returned dict keys are absolute filesystem paths. The code uses `os.path.join(proj_dir, file_path)` but does not ensure the result is absolute; passing a relative `proj_dir` produces relative keys, violating the specification.

---

## How to trigger the bug

Call `CodeGraphExtractor.get_functions_by_file(lang_key="python", proj_dir="relative/path")` where `proj_dir` is a relative path. The returned dictionary's keys will be relative paths like `"relative/path/test_module.py"` instead of absolute paths like `"/cwd/relative/path/test_module.py"`.

### Inputs

| Parameter | Value |
|-----------|-------|
| `lang_key` | `"python"` |
| `proj_dir` | `"relative/path"` (a relative filesystem path) |

### Expected (spec-correct) Output

`{"/cwd/relative/path/test_module.py": [("hello", "def hello():\n    return 'world'\n"), ...]}` — all dict keys are absolute filesystem paths.

### Actual (buggy) Output

`{"relative/path/test_module.py": [("hello", "def hello():\n    return 'world'\n"), ...]}` — dict key is a relative path (not absolute).

### How to Reproduce

1. Navigate to the repo root.
2. Create a codegraph SQLite database with test data referencing source files.
3. Run the following snippet (uses the public API):

```python
from src.languages.codegraph import CodeGraphExtractor

extractor = CodeGraphExtractor("path/to/.codegraph/codegraph.db")
result = extractor.get_functions_by_file("python", proj_dir="relative/path")

# actual (buggy) output: keys are relative paths like "relative/path/test_module.py"
# expected (correct) output: keys should be absolute paths like "/cwd/relative/path/test_module.py"
print(result.keys())
```

---

## Probe Script

```python
import os
import sys
import sqlite3
import tempfile
import shutil

# Add repo root to Python path so `from src.languages.codegraph import ...` works
repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, repo_root)

try:
    from src.languages.codegraph import CodeGraphExtractor

    # --- Setup: create a temporary directory with test fixtures ---
    tmpdir = tempfile.mkdtemp(prefix="probe_cg_")
    cg_dir = os.path.join(tmpdir, ".codegraph")
    os.makedirs(cg_dir, exist_ok=True)
    db_path = os.path.join(cg_dir, "codegraph.db")

    # Create the codegraph SQLite database with the nodes table
    conn = sqlite3.connect(db_path)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS nodes (
            id INTEGER PRIMARY KEY,
            name TEXT,
            qualified_name TEXT,
            file_path TEXT,
            start_line INTEGER,
            end_line INTEGER,
            kind TEXT,
            language TEXT
        )
    """)

    # Create a small Python source file as a test subject
    test_src = os.path.join(tmpdir, "test_module.py")
    with open(test_src, "w") as f:
        f.write("def hello():\n    return 'world'\n\n")
        f.write("def goodbye():\n    return 'farewell'\n")

    # Insert function entries referencing the test source file
    conn.execute(
        "INSERT INTO nodes (name, qualified_name, file_path, start_line, end_line, kind, language) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        ("hello", "hello", "test_module.py", 1, 2, "function", "python"),
    )
    conn.execute(
        "INSERT INTO nodes (name, qualified_name, file_path, start_line, end_line, kind, language) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        ("goodbye", "goodbye", "test_module.py", 4, 5, "function", "python"),
    )
    conn.commit()
    conn.close()

    # --- Test: call get_functions_by_file with a RELATIVE proj_dir ---
    cwd = os.getcwd()
    rel_proj_dir = os.path.relpath(tmpdir, cwd)

    extractor = CodeGraphExtractor(db_path)
    result = extractor.get_functions_by_file("python", proj_dir=rel_proj_dir)

    # --- Oracle: spec requires ALL keys to be absolute filesystem paths ---
    bug_confirmed = False
    non_absolute_keys = []

    for key in result:
        if not os.path.isabs(key):
            non_absolute_keys.append(key)
            bug_confirmed = True

    expected = os.path.abspath(os.path.join(rel_proj_dir, "test_module.py"))

    if bug_confirmed:
        print(
            f"CONFIRMED — spec requires absolute paths as dict keys, "
            f"but passing a relative proj_dir={rel_proj_dir!r} produced "
            f"relative key: {non_absolute_keys!r} instead of expected absolute key {expected!r}"
        )
    else:
        print(f"NOT CONFIRMED — all keys are absolute: {list(result.keys())!r}")

except Exception as e:
    import traceback
    print(f"ERROR: {e}")
    traceback.print_exc()
    sys.exit(1)
finally:
    if "tmpdir" in dir():
        shutil.rmtree(tmpdir, ignore_errors=True)
```

### Probe Output

```
CONFIRMED — spec requires absolute paths as dict keys, but passing a relative proj_dir='../../probe_cg_bq8naau0' produced relative key: ['../../probe_cg_bq8naau0/test_module.py'] instead of expected absolute key '/tmp/probe_cg_bq8naau0/test_module.py'
```

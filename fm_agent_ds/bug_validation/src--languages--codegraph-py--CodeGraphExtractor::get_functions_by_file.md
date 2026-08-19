# Bug Report: CodeGraphExtractor::get_functions_by_file

**Source file:** `src/languages/codegraph.py` (line 299)
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

When lang_key is recognized by the code analysis backend: returns a dictionary mapping each absolute source file path (str) to a list of (function_name: str, body_text: str) tuples. Each tuple corresponds to one function or method definition in that file. function_name is a class-qualified identifier for methods or a bare function name for free functions; when multiple definitions share the same function_name within the same file, the first occurrence retains the bare name and all subsequent occurrences append a deterministic underscore-suffixed numeric index (beginning with _1) by source-order position. body_text is the complete source text of the function definition from its starting line through its ending line, with a trailing newline. Files present in the index but unreadable on disk are excluded from the returned dictionary. Returns an empty dictionary when lang_key is not recognized by the code analysis backend.

---

### Actual Behavior

If _CG_LANG.get(lang_key) is falsy (None or empty), the method returns an empty dictionary and no database connection is opened. Otherwise, a SQLite connection to self._db is opened; if a sqlite3.Error or other unhandled exception occurs during the database operations (connect, cursor, execute, fetchall) or before the explicit close, the connection may not be closed, no return value is produced, and the exception propagates. If the database interaction completes without exception, the connection is closed after fetching all rows ordered by file_path, start_line. The rows are grouped by file_path into a mapping (by_file), preserving the row order, where each value is a list of tuples (ident, start_line, end_line) with ident = _extraction_ident(name, qualified_name) and start_line/end_line converted to int. Then an empty dictionary result is built. For each file_path in by_file, abs_path is computed as os.path.join(proj_dir, file_path) if proj_dir is not None, else file_path. An attempt is made to open abs_path in text mode with errors='replace'; if an OSError occurs, the file is skipped (continue), leaving the result unchanged for that path. If the file is opened successfully, its lines are read. Then for each function entry in the per-file list (ordered by start_line), a deduplicated identifier deduped is generated: if the identifier ident has appeared count times before in the same file (tracked per file), deduped = ident if count == 0 else f"{ident}_{count}". The body is extracted as the concatenation of lines[start_line - 1 : end_line]; if the resulting body does not end with '\n', a newline is appended. The pair (deduped, body) is appended to a list file_funcs in that order. After processing all functions for the file, result[abs_path] is set to file_funcs. Once all files are processed, the method returns result. If any other unexpected exception occurs during file processing after the database phase, it propagates and no return occurs.

---

## Code Evidence

Line 299: `abs_path = os.path.join(proj_dir, file_path) if proj_dir else file_path`

When `proj_dir` is `None`, `abs_path` becomes the raw relative `file_path` stored in codegraph's database. This relative path is then used as a key in the returned dictionary, violating the specification's requirement that all keys be absolute file paths.

---

## Trigger Condition

The specification requires the returned dictionary to map absolute source file paths, but when proj_dir is None, the path used is the raw relative file_path, violating the absolute requirement.

---

## How to trigger the bug

Call `get_functions_by_file` with a valid `lang_key` and `proj_dir=None`. When the codegraph database contains function entries, the resulting dictionary keys will be relative paths instead of absolute paths.

### Inputs

| Parameter | Value |
|-----------|-------|
| `lang_key` | `"python"` |
| `proj_dir` | `None` |

### Expected (spec-correct) Output

All dictionary keys are absolute file paths (e.g. `/tmp/abc123/test_module.py`).

### Actual (buggy) Output

Dictionary keys are relative file paths (e.g. `test_module.py`).

### How to Reproduce

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import os
import tempfile
import sqlite3
from src.languages.codegraph import CodeGraphExtractor

tmpdir = tempfile.mkdtemp()
with open(os.path.join(tmpdir, "test_module.py"), "w") as f:
    f.write("def hello(name):\n    return f'Hello, {name}!'\n")

db_path = os.path.join(tmpdir, "codegraph.db")
conn = sqlite3.connect(db_path)
conn.execute("CREATE TABLE nodes (id INTEGER PRIMARY KEY, name TEXT, qualified_name TEXT, file_path TEXT, kind TEXT, language TEXT, start_line INTEGER, end_line INTEGER)")
conn.execute("INSERT INTO nodes VALUES (1, 'hello', 'hello', 'test_module.py', 'function', 'python', 1, 2)")
conn.commit()
conn.close()

extractor = CodeGraphExtractor(db_path)
old = os.getcwd()
os.chdir(tmpdir)
result = extractor.get_functions_by_file("python", proj_dir=None)
os.chdir(old)

print(list(result.keys()))
# actual (buggy) output: ['test_module.py']
# expected (correct) output: ['/tmp/.../test_module.py'] (absolute path)
```

---

## Probe Script

```py
"""Probe script for bug: src--languages--codegraph-py--CodeGraphExtractor::get_functions_by_file

The spec claims get_functions_by_file returns a dictionary mapping each absolute
source file path (str) to a list of (function_name, body_text) tuples. The actual
code uses ``os.path.join(proj_dir, file_path) if proj_dir else file_path``, so
when proj_dir is None the dict keys are raw relative file_path values instead of
absolute paths.

Strategy: create a temp workspace with a test source file and a minimal codegraph
SQLite database, call get_functions_by_file with proj_dir=None from that temp
directory (so the relative path resolves), and check whether the returned dict
keys are absolute paths.
"""
import sys
import os
import sqlite3
import tempfile
import traceback

# Probe is at <repo>/fm_agent/bug_validation/probe_*.py
# Go up 3 levels to reach repo root
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _REPO_ROOT)

try:
    from src.languages.codegraph import CodeGraphExtractor

    # Create a self-contained temporary directory for all file I/O
    tmpdir = tempfile.mkdtemp()

    # Create a test source file in the temp dir with a simple function
    test_file = os.path.join(tmpdir, "test_module.py")
    with open(test_file, "w") as f:
        f.write("def hello(name):\n    return f'Hello, {name}!'\n")

    # Create a minimal codegraph SQLite database
    db_path = os.path.join(tmpdir, "codegraph.db")
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE nodes (
            id INTEGER PRIMARY KEY,
            name TEXT,
            qualified_name TEXT,
            file_path TEXT,
            kind TEXT,
            language TEXT,
            start_line INTEGER,
            end_line INTEGER
        )
    """)

    # Insert a function node with a relative file_path (as codegraph stores)
    rel_file = "test_module.py"
    cur.execute(
        "INSERT INTO nodes (name, qualified_name, file_path, kind, language, start_line, end_line) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        ("hello", "hello", rel_file, "function", "python", 1, 2),
    )
    conn.commit()
    conn.close()

    extractor = CodeGraphExtractor(db_path)

    # Change into the temp dir so that the relative file_path resolves
    # correctly when proj_dir=None (the abs_path becomes just file_path,
    # which is valid relative to CWD).
    old_cwd = os.getcwd()
    os.chdir(tmpdir)
    try:
        result = extractor.get_functions_by_file("python", proj_dir=None)
    finally:
        os.chdir(old_cwd)

    # The spec claims ALL keys MUST be absolute paths.
    if not result:
        print("NOT CONFIRMED — result was empty (no functions extracted)")
    else:
        abs_keys = [k for k in result.keys() if os.path.isabs(k)]
        rel_keys = [k for k in result.keys() if not os.path.isabs(k)]
        if rel_keys:
            print(
                f"CONFIRMED — returned dict keys are not all absolute: "
                f"relative keys={rel_keys!r}, "
                f"absolute keys={abs_keys!r}"
            )
        else:
            print(f"NOT CONFIRMED — all {len(result)} returned keys are absolute paths")

except Exception as e:
    print(f"ERROR: {e}")
    traceback.print_exc()
    sys.exit(1)
```

### Probe Output

```
CONFIRMED — returned dict keys are not all absolute: relative keys=['test_module.py'], absolute keys=[]
```

# Bug Report: batch_extract

**Source file:** `/home/fancy/Projects_Vault/FM-Agent/fm_agent/extracted_functions/src/languages/python-py/batch_extract.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

Returns a dictionary whose keys are absolute file paths (str) for every Python source file discovered in proj_dir. The value for each key is a list of (func_name: str, func_body: str) 2-tuples, one tuple per function defined in that file. A file containing no function definitions yields an empty list. When the static-analysis backend cannot initialize, returns an empty dictionary.

---

### Actual Behavior

After execution, if no exception occurs, the function returns a dictionary. Let cg = CodeGraphExtractor.from_proj_dir(proj_dir). If cg is not None, the returned dictionary R equals cg.get_functions_by_file('python', proj_dir); i.e., for each absolute file path p of a Python source file under proj_dir, R[p] is a list of (func_name, func_body) tuples for all functions in that file. If cg is None, then R = {}. If an exception is raised during from_proj_dir or get_functions_by_file, the exception propagates and batch_extract returns no value.

Formal logic:
Normal termination: ( cg  {CodeGraphExtractor, None}. cg = CodeGraphExtractor.from_proj_dir(proj_dir)  ( (cg  None  R = cg.get_functions_by_file('python', proj_dir))  (cg = None  R = {}) ) ).
Abnormal termination: An exception E is raised, and the function stack is unwound.

---

## Code Evidence

Line 4: return cg.get_functions_by_file("python", proj_dir) if cg else {}

---

## Trigger Condition

The specification mandates that every Python file in the project is a key, with an empty list if no functions are present. The implementation relies on get_functions_by_file, which may only include files that contain at least one function, thus omitting files without functions.

---

## How to trigger the bug

The probed considered the case where `proj_dir` contains two Python source files: `has_funcs.py` (which defines one function, `hello`) and `no_funcs.py` (which contains only global statements — no function definitions). The mock codegraph database included only the node for `hello` from `has_funcs.py`, consistent with real codegraph behavior that only stores function/method nodes. When `batch_extract(proj_dir)` was called, `get_functions_by_file` queried the nodes table for Python function/method nodes, found only the entry for `has_funcs.py`, and returned a dictionary keyed solely by `has_funcs.py`. The file `no_funcs.py` was silently omitted, violating the specification's requirement that every Python file must appear as a key.

### Inputs

| Parameter | Value |
|-----------|-------|
| `proj_dir` | Path to a temporary directory containing `has_funcs.py` (with a function) and `no_funcs.py` (without functions), with a codegraph database indexing only the function in `has_funcs.py`. |

### Expected (spec-correct) Output

A dictionary containing both file paths as keys:

```
{".../has_funcs.py": [("hello", "def hello():\n    return 'world'\n")], ".../no_funcs.py": []}
```

### Actual (buggy) Output

A dictionary containing only the file with functions:

```
{".../has_funcs.py": [("hello", "def hello():\n    return 'world'\n")]}
```

`no_funcs.py` is absent from the result.

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Create a temporary project with a Python file that has functions and one that does not, and build the codegraph index.
3. Run the following snippet (uses the package entry point):

```python
import os, sys, tempfile, shutil, sqlite3, uuid, time

# Add repo root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from src.languages.python import batch_extract

# Create a temp project
tmpdir = tempfile.mkdtemp()

# Write a file WITH a function
with open(os.path.join(tmpdir, "has_funcs.py"), "w") as f:
    f.write("def hello():\n    return 'world'\n")

# Write a file WITHOUT any function
with open(os.path.join(tmpdir, "no_funcs.py"), "w") as f:
    f.write("x = 1\n")

# Create codegraph index (or mock DB)
cg_dir = os.path.join(tmpdir, ".codegraph")
os.makedirs(cg_dir)
conn = sqlite3.connect(os.path.join(cg_dir, "codegraph.db"))
cur = conn.cursor()
cur.execute("""CREATE TABLE nodes (
    id TEXT PRIMARY KEY, kind TEXT, name TEXT, qualified_name TEXT,
    file_path TEXT, language TEXT, start_line INTEGER, end_line INTEGER,
    start_column INTEGER DEFAULT 0, end_column INTEGER DEFAULT 0,
    updated_at INTEGER)""")
cur.execute("INSERT INTO nodes VALUES (?, 'function', ?, ?, ?, ?, ?, ?, 0, 0, ?)",
    (str(uuid.uuid4()), 'hello', 'hello', 'has_funcs.py', 'python', 1, 2, int(time.time())))
conn.commit()
conn.close()

result = batch_extract(tmpdir)
# actual (buggy) output: {".../has_funcs.py": [...]}   — no_funcs.py is MISSING
# expected (correct) output: {".../has_funcs.py": [...], ".../no_funcs.py": []}
print("no_funcs.py present?", os.path.join(tmpdir, "no_funcs.py") in result)
# prints: False

shutil.rmtree(tmpdir)
```

---

## Probe Script

```python
"""Probe script for bug: src--languages--python-py--batch_extract

Bug: batch_extract() requires every Python file in the project to be a key
with an empty list when no functions are present.  The implementation delegates to
get_functions_by_file, which only includes files that have >=1 function/method
node in codegraph.  Files without functions are silently omitted.
"""
import sys
import os
import tempfile
import shutil
import sqlite3
import uuid
import time
import traceback

# Probe at <repo>/fm_agent/bug_validation/probe_*.py → go up 3 levels
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _REPO_ROOT)

try:
    from src.languages.python import batch_extract
except Exception as e:
    print(f"ERROR: Failed to import batch_extract: {e}")
    sys.exit(1)


def _make_codegraph_db(db_dir, nodes_data):
    """Create a minimal .codegraph/codegraph.db with a nodes table.

    nodes_data: list of (name, qualified_name, file_path, language,
                         start_line, end_line) tuples.
    """
    cg_dir = os.path.join(db_dir, ".codegraph")
    os.makedirs(cg_dir, exist_ok=True)
    db_path = os.path.join(cg_dir, "codegraph.db")

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS nodes (
            id TEXT PRIMARY KEY,
            kind TEXT NOT NULL,
            name TEXT NOT NULL,
            qualified_name TEXT NOT NULL,
            file_path TEXT NOT NULL,
            language TEXT NOT NULL,
            start_line INTEGER NOT NULL,
            end_line INTEGER NOT NULL,
            start_column INTEGER NOT NULL DEFAULT 0,
            end_column INTEGER NOT NULL DEFAULT 0,
            updated_at INTEGER NOT NULL
        )
    """)

    now = int(time.time())
    for (name, qname, fpath, lang, sl, el) in nodes_data:
        cur.execute(
            """INSERT INTO nodes
               (id, kind, name, qualified_name, file_path, language,
                start_line, end_line, start_column, end_column, updated_at)
               VALUES (?, 'function', ?, ?, ?, ?, ?, ?, 0, 0, ?)""",
            (str(uuid.uuid4()), name, qname, fpath, lang, sl, el, now),
        )

    conn.commit()
    conn.close()
    return db_path


def _run_test(label, src_files, nodes_data):
    """Create a temp project, run batch_extract, and check for empty lists."""
    tmpdir = tempfile.mkdtemp(prefix="probe_py_batch_extract_")
    try:
        for relpath, content in src_files.items():
            abs_path = os.path.join(tmpdir, relpath)
            os.makedirs(os.path.dirname(abs_path), exist_ok=True)
            with open(abs_path, "w") as f:
                f.write(content)

        _make_codegraph_db(tmpdir, nodes_data)
        result_dict = batch_extract(tmpdir)

        # Files with functions should be present
        # Files without functions (no codegraph nodes) should have empty lists
        # Bug is: files without functions are missing entirely
        all_py_files = [
            os.path.join(tmpdir, p) for p in src_files
            if p.endswith(".py")
        ]
        present = set(result_dict.keys())
        missing = [p for p in all_py_files if p not in present]
        empty_lists = [p for p in present if len(result_dict[p]) == 0]

        if missing:
            return {
                "label": label,
                "classification": "confirmed",
                "stdout": (
                    f"CONFIRMED — {len(missing)} Python file(s) missing from "
                    f"result dict: {[os.path.basename(p) for p in missing]}. "
                    f"Present: {[os.path.basename(p) for p in sorted(present)]}. "
                    f"Spec requires every Python file to be a key."
                ),
            }
        else:
            counts = {os.path.basename(k): len(v) for k, v in result_dict.items()}
            if not result_dict:
                return {
                    "label": label,
                    "classification": "not_confirmed",
                    "stdout": "NOT CONFIRMED — batch_extract returned an empty dict",
                }
            else:
                return {
                    "label": label,
                    "classification": "not_confirmed",
                    "stdout": (
                        f"NOT CONFIRMED — all {len(result_dict)} file(s) present: {counts}"
                    ),
                }
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def main():
    max_attempts = 10
    final_result = None

    test_cases = [
        # Attempt 1: one file WITH functions (has codegraph nodes),
        # one file WITHOUT functions (NO codegraph nodes).
        {
            "label": "Single file with functions + empty file without",
            "src_files": {
                "has_funcs.py": (
                    "def hello():\n"
                    "    return 'world'\n"
                ),
                "no_funcs.py": (
                    "import os\n"
                    "x = 1\n"
                ),
            },
            "nodes": [
                ("hello", "hello", "has_funcs.py", "python", 1, 2),
            ],
        },
        # Attempt 2: empty .py file
        {
            "label": "Function file + completely empty file",
            "src_files": {
                "has_funcs.py": "def foo():\n    pass\n",
                "empty.py": "",
            },
            "nodes": [
                ("foo", "foo", "has_funcs.py", "python", 1, 2),
            ],
        },
        # Attempt 3: multiple function files + no-function file
        {
            "label": "Two function files + one no-function file",
            "src_files": {
                "a.py": "def alpha():\n    return 1\n",
                "b.py": "def beta():\n    return 2\n",
                "only_vars.py": "CONFIG = True\nDEBUG = False\n",
            },
            "nodes": [
                ("alpha", "alpha", "a.py", "python", 1, 2),
                ("beta", "beta", "b.py", "python", 1, 2),
            ],
        },
        # Attempt 4: class methods (method kind, not just function)
        {
            "label": "Class methods present, no-function file absent",
            "src_files": {
                "klass.py": (
                    "class Foo:\n"
                    "    def method(self):\n"
                    "        pass\n"
                ),
                "globals_only.py": "VERSION = '1.0'\n",
            },
            "nodes": [
                ("method", "Foo.method", "klass.py", "python", 2, 3),
            ],
        },
        # Attempt 5: no-function file ONLY (edge case: single file with no functions)
        {
            "label": "Single file with no functions at all",
            "src_files": {
                "constants.py": "PI = 3.14\nE = 2.718\n",
            },
            "nodes": [],  # No nodes at all
        },
        # Attempt 6: subdirectory with no-function file
        {
            "label": "Subdirectory: function file + separate no-function file",
            "src_files": {
                "main.py": "def main():\n    pass\n",
                "utils/__init__.py": "from .constants import *\n",
                "utils/constants.py": "MAX_SIZE = 1024\n",
            },
            "nodes": [
                ("main", "main", "main.py", "python", 1, 2),
            ],
        },
    ]

    for attempt_idx, tc in enumerate(test_cases):
        result = _run_test(tc["label"], tc["src_files"], tc["nodes"])
        final_result = result

        if result["classification"] == "confirmed":
            print(result["stdout"])
            return

    # All attempts exhausted without confirmation
    if final_result is not None:
        print(final_result["stdout"])


if __name__ == "__main__":
    main()
```

### Probe Output

```
CONFIRMED — 1 Python file(s) missing from result dict: ['no_funcs.py']. Present: ['has_funcs.py']. Spec requires every Python file to be a key.
```

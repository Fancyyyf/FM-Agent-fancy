# Bug Report: batch_extract

**Source file:** `/home/fancy/Projects_Vault/FM-Agent/fm_agent/extracted_functions/src/languages/cpp-py/batch_extract.py`
**Verdict:** MISMATCH
**Confirmation status:** not_confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

Returns a dictionary mapping absolute filesystem paths (str) to lists of (function_name: str, body_text: str) tuples for all C++ source files identified in proj_dir and its subdirectories. If the CodeGraph extraction backend is unavailable or fails to initialize for the project, returns an empty dictionary. Each key in the returned dictionary is an absolute path to a C++ source file that contains at least one function definition; each associated value is a non-empty list of (func_name, body) tuples extracted from that file.

---

### Actual Behavior

If no exception occurs, the function returns a dictionary. Let cg = CodeGraphExtractor.from_proj_dir(proj_dir). If cg is not None, the returned dictionary is cg.get_functions_by_file("cpp", proj_dir), which maps each absolute file path (str) of a C++ source file within proj_dir or its subdirectories to a list of (function_name: str, body_text: str) tuples. If cg is None, the function returns an empty dictionary {}. No side effects are produced, and the precondition that proj_dir is an existing directory is preserved.

---

## Code Evidence

Line 4: return cg.get_functions_by_file("cpp", proj_dir) if cg else {}

---

## Trigger Condition

The specification requires each value in the returned dictionary to be a non-empty list of extracted function tuples and that each key corresponds to a file containing at least one function definition. The code returns the raw output of get_functions_by_file, which can include source files that have no function definitions with empty lists, violating the specification.

---

## How to trigger the bug

Despite the theoretical concern raised by the logic verifier, the bug could not be reproduced in practice. Across 10 attempts with varied edge cases — including normal C++ files, empty files, malformed CodeGraph database entries (start_line > end_line, line ranges beyond file content, empty function names, non-existent source files), and qualified class methods — `get_functions_by_file` consistently produces non-empty lists for every file it includes. The function only includes files that have at least one function/method node in the CodeGraph database, and for each such file it always adds entries to the per-file function list. Files without function definitions are simply not included in the returned dictionary at all.

### Inputs

| Parameter | Value |
|-----------|-------|
| `proj_dir` | A temporary directory containing C++ source files and a valid `.codegraph/codegraph.db` |

### Expected (spec-correct) Output

A dictionary where every value is a non-empty list of `(func_name, body)` tuples.

### Actual (buggy) Output

The dictionary produced by `get_functions_by_file` contains only non-empty lists in all tested scenarios. No empty-list values were observed.

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import tempfile, os, sqlite3, uuid, time
from src.languages.cpp import batch_extract

tmpdir = tempfile.mkdtemp()
os.makedirs(os.path.join(tmpdir, ".codegraph"), exist_ok=True)

# Create codegraph DB with function nodes
conn = sqlite3.connect(os.path.join(tmpdir, ".codegraph", "codegraph.db"))
conn.execute("""
    CREATE TABLE IF NOT EXISTS nodes (
        id TEXT PRIMARY KEY, kind TEXT, name TEXT, qualified_name TEXT,
        file_path TEXT, language TEXT, start_line INTEGER, end_line INTEGER,
        start_column INTEGER, end_column INTEGER, updated_at INTEGER
    )
""")
with open(os.path.join(tmpdir, "test.cpp"), "w") as f:
    f.write("int add(int a, int b) {\n    return a + b;\n}\n")
conn.execute("INSERT INTO nodes VALUES (?,?,?,?,?,?,?,?,?,?,?)",
    (str(uuid.uuid4()), "function", "add", "add", "test.cpp", "cpp", 1, 3, 0, 0, int(time.time())))
conn.commit()
conn.close()

result = batch_extract(tmpdir)
# Check for empty lists
empty = [fp for fp, funcs in result.items() if len(funcs) == 0]
print(f"Empty lists: {empty}")  # Expected: [] — bug would mean non-empty
# actual output: Empty lists: []
# expected (if bug exists): Empty lists: ['.../test.cpp']
```

---

## Probe Script

```python
import sys
import os
import tempfile
import shutil
import sqlite3
import uuid
import time

# Ensure the repo root is on sys.path so we can import the package
repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, repo_root)

try:
    from src.languages.cpp import batch_extract
except Exception as e:
    print(f"ERROR: Failed to import batch_extract: {e}")
    sys.exit(1)


def create_codegraph_db(db_dir, nodes_data):
    """Create a minimal .codegraph/codegraph.db with nodes for testing."""
    codegraph_dir = os.path.join(db_dir, ".codegraph")
    os.makedirs(codegraph_dir, exist_ok=True)
    db_path = os.path.join(codegraph_dir, "codegraph.db")

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS nodes (
            id TEXT PRIMARY KEY, kind TEXT NOT NULL, name TEXT NOT NULL,
            qualified_name TEXT NOT NULL, file_path TEXT NOT NULL,
            language TEXT NOT NULL, start_line INTEGER NOT NULL,
            end_line INTEGER NOT NULL, start_column INTEGER NOT NULL,
            end_column INTEGER NOT NULL, docstring TEXT, signature TEXT,
            visibility TEXT, is_exported INTEGER DEFAULT 0,
            is_async INTEGER DEFAULT 0, is_static INTEGER DEFAULT 0,
            is_abstract INTEGER DEFAULT 0, decorators TEXT,
            type_parameters TEXT, return_type TEXT, updated_at INTEGER NOT NULL
        )
    """)

    now = int(time.time())
    for nd in nodes_data:
        node_id = str(uuid.uuid4())
        cur.execute(
            """INSERT INTO nodes
               (id, kind, name, qualified_name, file_path, language,
                start_line, end_line, start_column, end_column, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (node_id, "function", nd["name"],
             nd.get("qualified_name", nd["name"]), nd["file_path"],
             nd["language"], nd["start_line"], nd["end_line"],
             nd.get("start_column", 0), nd.get("end_column", 0), now),
        )

    conn.commit()
    conn.close()
    return db_path


def run_test(label, src_files, nodes_data):
    """Run a single test: create temp dir with source files + codegraph DB,
    call batch_extract, check for empty lists."""
    tmpdir = tempfile.mkdtemp(prefix="probe_batch_extract_")
    try:
        for relpath, content in src_files.items():
            abs_path = os.path.join(tmpdir, relpath)
            os.makedirs(os.path.dirname(abs_path), exist_ok=True)
            with open(abs_path, "w") as f:
                f.write(content)

        create_codegraph_db(tmpdir, nodes_data)
        result_dict = batch_extract(tmpdir)

        empty_files = [fp for fp, funcs in result_dict.items() if len(funcs) == 0]
        if empty_files:
            return {
                "label": label,
                "classification": "confirmed",
                "stdout": f"CONFIRMED — batch_extract returned empty lists for files: {empty_files}",
            }
        else:
            counts = {os.path.basename(k): len(v) for k, v in result_dict.items()}
            if not result_dict:
                return {
                    "label": label,
                    "classification": "not_confirmed",
                    "stdout": "NOT CONFIRMED — batch_extract returned an empty dict (no files)",
                }
            else:
                return {
                    "label": label,
                    "classification": "not_confirmed",
                    "stdout": f"NOT CONFIRMED — all {len(result_dict)} files have non-empty function lists: {counts}",
                }
    except Exception as e:
        import traceback
        return {
            "label": label,
            "classification": "error",
            "stdout": f"ERROR: {e}\n{traceback.format_exc()}",
        }
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def main():
    max_attempts = 10
    final_result = None
    attempts = 0

    test_cases = [
        {
            "label": "Normal: C++ file with functions in codegraph DB",
            "src_files": {
                "has_funcs.cpp": (
                    "// header\n#include <iostream>\n\n"
                    "int add(int a, int b) {\n    return a + b;\n}\n\n"
                    "void greet() {\n    std::cout << \"hello\" << std::endl;\n}\n"
                ),
                "no_funcs.cpp": "#include <string>\nstatic const int MAGIC = 42;\n",
            },
            "nodes": [
                {"name": "add", "qualified_name": "add", "file_path": "has_funcs.cpp",
                 "language": "cpp", "start_line": 4, "end_line": 6, "start_column": 0, "end_column": 1},
                {"name": "greet", "qualified_name": "greet", "file_path": "has_funcs.cpp",
                 "language": "cpp", "start_line": 8, "end_line": 10, "start_column": 0, "end_column": 1},
            ],
        },
        {
            "label": "Single-line function: start_line == end_line",
            "src_files": {"single.cpp": "void empty() {}\nvoid another() { return; }\n"},
            "nodes": [
                {"name": "empty", "qualified_name": "empty", "file_path": "single.cpp",
                 "language": "cpp", "start_line": 1, "end_line": 1, "start_column": 0, "end_column": 14},
                {"name": "another", "qualified_name": "another", "file_path": "single.cpp",
                 "language": "cpp", "start_line": 1, "end_line": 1, "start_column": 15, "end_column": 36},
            ],
        },
        {
            "label": "Malformed: start_line > end_line",
            "src_files": {"bad.cpp": "int f() { return 0; }\n"},
            "nodes": [
                {"name": "f", "qualified_name": "f", "file_path": "bad.cpp",
                 "language": "cpp", "start_line": 5, "end_line": 1, "start_column": 0, "end_column": 20},
            ],
        },
        {
            "label": "Line ranges beyond file content",
            "src_files": {"short.cpp": "int a = 1;\n"},
            "nodes": [
                {"name": "phantom", "qualified_name": "phantom", "file_path": "short.cpp",
                 "language": "cpp", "start_line": 100, "end_line": 200, "start_column": 0, "end_column": 1},
            ],
        },
        {
            "label": "Empty source file with function DB entries",
            "src_files": {"empty.cpp": ""},
            "nodes": [
                {"name": "ghost", "qualified_name": "ghost", "file_path": "empty.cpp",
                 "language": "cpp", "start_line": 1, "end_line": 5, "start_column": 0, "end_column": 1},
            ],
        },
        {
            "label": "Non-existent source file with function DB entries",
            "src_files": {"real.cpp": "void real() { return; }\n"},
            "nodes": [
                {"name": "fake", "qualified_name": "fake", "file_path": "missing.cpp",
                 "language": "cpp", "start_line": 1, "end_line": 3, "start_column": 0, "end_column": 1},
                {"name": "real", "qualified_name": "real", "file_path": "real.cpp",
                 "language": "cpp", "start_line": 1, "end_line": 1, "start_column": 0, "end_column": 22},
            ],
        },
        {
            "label": "Empty function name in DB",
            "src_files": {"weird.cpp": "int x() { return 1; }\n"},
            "nodes": [
                {"name": "", "qualified_name": "", "file_path": "weird.cpp",
                 "language": "cpp", "start_line": 1, "end_line": 1, "start_column": 0, "end_column": 20},
            ],
        },
        {
            "label": "Operator-like empty name: parentheses only",
            "src_files": {"ops.cpp": "struct S { void operator()() {} };\n"},
            "nodes": [
                {"name": "operator()", "qualified_name": "S::operator()", "file_path": "ops.cpp",
                 "language": "cpp", "start_line": 1, "end_line": 1, "start_column": 16, "end_column": 35},
            ],
        },
        {
            "label": "Subdirectory: file in nested directory",
            "src_files": {
                "src/core/util.cpp": "int util() { return 42; }\n",
                "src/main.cpp": "int main() { return 0; }\n",
            },
            "nodes": [
                {"name": "util", "qualified_name": "util", "file_path": "src/core/util.cpp",
                 "language": "cpp", "start_line": 1, "end_line": 1, "start_column": 0, "end_column": 22},
                {"name": "main", "qualified_name": "main", "file_path": "src/main.cpp",
                 "language": "cpp", "start_line": 1, "end_line": 1, "start_column": 0, "end_column": 22},
            ],
        },
        {
            "label": "Class methods with qualified names",
            "src_files": {
                "klass.cpp": "class Widget {\npublic:\n  void paint() {}\n  int size() { return 0; }\n};\n",
            },
            "nodes": [
                {"name": "paint", "qualified_name": "Widget::paint", "file_path": "klass.cpp",
                 "language": "cpp", "start_line": 3, "end_line": 3, "start_column": 7, "end_column": 20},
                {"name": "size", "qualified_name": "Widget::size", "file_path": "klass.cpp",
                 "language": "cpp", "start_line": 4, "end_line": 4, "start_column": 6, "end_column": 20},
            ],
        },
    ]

    for attempt_idx, tc in enumerate(test_cases):
        attempts += 1
        print(f"\n--- Attempt {attempts}: {tc['label']} ---")

        result = run_test(tc["label"], tc["src_files"], tc["nodes"])
        final_result = result
        print(f"  => {result['classification'].upper()}: {result['stdout']}")

        if result["classification"] == "confirmed":
            break

    print(f"\n{'='*60}")
    print(f"FINAL: {final_result['classification'].upper()}")
    print(f"{final_result['stdout']}")


if __name__ == "__main__":
    main()
```

### Probe Output

```

--- Attempt 1: Normal: C++ file with functions in codegraph DB ---
  => NOT_CONFIRMED: NOT CONFIRMED — all 1 files have non-empty function lists: {'has_funcs.cpp': 2}

--- Attempt 2: Single-line function: start_line == end_line ---
  => NOT_CONFIRMED: NOT CONFIRMED — all 1 files have non-empty function lists: {'single.cpp': 2}

--- Attempt 3: Malformed: start_line > end_line ---
  => NOT_CONFIRMED: NOT CONFIRMED — all 1 files have non-empty function lists: {'bad.cpp': 1}

--- Attempt 4: Line ranges beyond file content ---
  => NOT_CONFIRMED: NOT CONFIRMED — all 1 files have non-empty function lists: {'short.cpp': 1}

--- Attempt 5: Empty source file with function DB entries ---
  => NOT_CONFIRMED: NOT CONFIRMED — all 1 files have non-empty function lists: {'empty.cpp': 1}

--- Attempt 6: Non-existent source file with function DB entries ---
  => NOT_CONFIRMED: NOT CONFIRMED — all 1 files have non-empty function lists: {'real.cpp': 1}

--- Attempt 7: Empty function name in DB ---
  => NOT_CONFIRMED: NOT CONFIRMED — all 1 files have non-empty function lists: {'weird.cpp': 1}

--- Attempt 8: Operator-like empty name: parentheses only ---
  => NOT_CONFIRMED: NOT CONFIRMED — all 1 files have non-empty function lists: {'ops.cpp': 1}

--- Attempt 9: Subdirectory: file in nested directory ---
  => NOT_CONFIRMED: NOT CONFIRMED — all 2 files have non-empty function lists: {'util.cpp': 1, 'main.cpp': 1}

--- Attempt 10: Class methods with qualified names ---
  => NOT_CONFIRMED: NOT CONFIRMED — all 1 files have non-empty function lists: {'klass.cpp': 2}

============================================================
FINAL: NOT_CONFIRMED
NOT CONFIRMED — all 1 files have non-empty function lists: {'klass.cpp': 2}
```

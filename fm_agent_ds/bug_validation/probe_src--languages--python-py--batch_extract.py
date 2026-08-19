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

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

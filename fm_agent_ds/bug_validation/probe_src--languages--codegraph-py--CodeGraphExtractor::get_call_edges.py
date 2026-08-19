"""Probe for bug: src--languages--codegraph-py--CodeGraphExtractor::get_call_edges

Bug: get_call_edges drops call edges where the callee is defined in a different
language than the requested language. _node_fqn_map only maps nodes of the
requested language, so fqn_of.get(tgt_id) returns None for callees in other
languages, and the edge is silently omitted.

The spec demands all direct call relationships where the CALLER is in the given
language, including calls to functions defined in other languages.
"""
import os
import sqlite3
import sys
import tempfile
import time

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, REPO_ROOT)

try:
    from src.languages.codegraph import CodeGraphExtractor

    # Build a synthetic codegraph database containing a cross-language call edge:
    # a Python function calls a C function.
    now = int(time.time() * 1000)
    python_node_id = "function:python-caller-001"
    c_node_id = "function:c-callee-001"

    with tempfile.TemporaryDirectory() as tmpdir:
        codegraph_dir = os.path.join(tmpdir, ".codegraph")
        os.makedirs(codegraph_dir, exist_ok=True)
        db_path = os.path.join(codegraph_dir, "codegraph.db")

        conn = sqlite3.connect(db_path)
        cur = conn.cursor()

        # Create schema matching codegraph's nodes and edges tables
        cur.executescript("""
            CREATE TABLE nodes (
                id TEXT PRIMARY KEY,
                kind TEXT NOT NULL,
                name TEXT NOT NULL,
                qualified_name TEXT NOT NULL,
                file_path TEXT NOT NULL,
                language TEXT NOT NULL,
                start_line INTEGER NOT NULL,
                end_line INTEGER NOT NULL,
                start_column INTEGER NOT NULL,
                end_column INTEGER NOT NULL,
                docstring TEXT,
                signature TEXT,
                visibility TEXT,
                is_exported INTEGER DEFAULT 0,
                is_async INTEGER DEFAULT 0,
                is_static INTEGER DEFAULT 0,
                is_abstract INTEGER DEFAULT 0,
                decorators TEXT,
                type_parameters TEXT,
                return_type TEXT,
                updated_at INTEGER NOT NULL
            );
            CREATE TABLE edges (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source TEXT NOT NULL,
                target TEXT NOT NULL,
                kind TEXT NOT NULL,
                metadata TEXT,
                line INTEGER,
                col INTEGER,
                provenance TEXT DEFAULT NULL,
                FOREIGN KEY (source) REFERENCES nodes(id) ON DELETE CASCADE,
                FOREIGN KEY (target) REFERENCES nodes(id) ON DELETE CASCADE
            );
        """)

        # Insert Python caller node
        cur.execute(
            """INSERT INTO nodes
               (id, kind, name, qualified_name, file_path, language,
                start_line, end_line, start_column, end_column, updated_at)
               VALUES (?, 'function', 'py_func', 'py_func', 'src/py_code.py',
                       'python', 1, 5, 0, 19, ?)""",
            (python_node_id, now),
        )

        # Insert C callee node
        cur.execute(
            """INSERT INTO nodes
               (id, kind, name, qualified_name, file_path, language,
                start_line, end_line, start_column, end_column, updated_at)
               VALUES (?, 'function', 'c_func', 'c_func', 'src/c_code.c',
                       'c', 1, 5, 0, 19, ?)""",
            (c_node_id, now),
        )

        # Insert the cross-language call edge: python_func -> c_func
        cur.execute(
            """INSERT INTO edges (source, target, kind)
               VALUES (?, ?, 'calls')""",
            (python_node_id, c_node_id),
        )

        conn.commit()
        conn.close()

        # Instantiate the extractor and call get_call_edges for Python
        extractor = CodeGraphExtractor(db_path)
        actual = extractor.get_call_edges("python")

        # Expected FQNs computed by _fqn_for:
        #   py_func at src/py_code.py → "src::py_code-py::py_func"
        #   c_func  at src/c_code.c   → "src::c_code-c::c_func"
        expected = {"src::py_code-py::py_func": {"src::c_code-c::c_func"}}

        # The bug: actual drops the cross-language edge because the C callee
        # is not in _node_fqn_map (only maps Python nodes).
        passed = actual != expected

        if passed:
            print(
                "CONFIRMED — Bug reproduced in attempt 1: "
                "cross-language call edge from Python to C was dropped. "
                f"actual={actual!r} | expected={expected!r}"
            )
        else:
            print(
                "NOT CONFIRMED — actual matched expected: "
                f"{actual!r}"
            )

except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

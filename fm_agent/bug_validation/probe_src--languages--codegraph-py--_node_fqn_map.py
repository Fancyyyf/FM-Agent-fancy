"""
Probe script for bug: src--languages--codegraph-py--_node_fqn_map

Tests whether _node_fqn_map crashes or returns an empty dict when called
with an empty cg_langs list.

Spec claim: "Returns an empty dict when the query matches no rows"
Trigger: empty cg_langs -> SQL ``language IN ()`` allegedly generates
         invalid SQL causing a crash per the bug claim.
"""
import sys
import os
import sqlite3

_PROJ_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _PROJ_ROOT not in sys.path:
    sys.path.insert(0, _PROJ_ROOT)

try:
    from src.languages.codegraph import _node_fqn_map

    conn = sqlite3.connect(":memory:")
    cur = conn.cursor()
    cur.execute(
        "CREATE TABLE nodes ("
        " id INTEGER, name TEXT, file_path TEXT, start_line INTEGER,"
        " kind TEXT, language TEXT"
        ")"
    )
    cur.execute(
        "INSERT INTO nodes VALUES (1, 'foo', '/a/b.py', 10, 'function', 'python')"
    )
    conn.commit()

    actual = _node_fqn_map(cur, [])
    expected = {}

    if actual == expected:
        print("NOT CONFIRMED — _node_fqn_map returned empty dict as spec requires")
        print(f"  actual: {actual!r}  expected: {expected!r}")
        print(f"  SQLite treats IN () as matching 0 rows (not a syntax error)")
    else:
        print(f"CONFIRMED — actual: {actual!r} | expected: {expected!r}")

except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

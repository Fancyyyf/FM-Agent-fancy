"""Probe script for bug: _node_fqn_map off-by-one deduplication suffix.

Bug: The deduplication counter c is 0-based but used directly as suffix,
     producing _1 for the 2nd occurrence instead of _2 per spec.

Spec says: k-th occurrence (1-indexed) gets suffix _k.
Code does: uses 0-based counter c directly → 2nd occurrence gets _1, 3rd gets _2.
"""

import sqlite3
import sys
import tempfile
import os

# Add repo root AND src/ to sys.path so we can import the project module.
# codegraph.py imports `config` (at repo root) so both need to be on path.
_proj_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_src_dir = os.path.join(_proj_root, "src")
for p in (_proj_root, _src_dir):
    if p not in sys.path:
        sys.path.insert(0, p)

try:
    from languages.codegraph import _node_fqn_map, _fqn_for
except ImportError as e:
    print(f"ERROR: Failed to import _node_fqn_map: {e}")
    sys.exit(1)

# Build a minimal in-memory SQLite database with the nodes table.
# We insert 3 function nodes sharing the same file_path and name to trigger
# the deduplication logic.
def run_test():
    conn = sqlite3.connect(":memory:")
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE nodes (
            id INTEGER PRIMARY KEY,
            name TEXT,
            qualified_name TEXT,
            file_path TEXT,
            start_line INTEGER,
            kind TEXT,
            language TEXT
        )
    """)

    # Three C functions: all named "helper", same file "src/util.c", same kind.
    # Inserted with different start_line to respect ORDER BY file_path, start_line.
    nodes = [
        (1, "helper", "helper", "src/util.c", 10, "function", "c"),
        (2, "helper", "helper", "src/util.c", 50, "function", "c"),
        (3, "helper", "helper", "src/util.c", 90, "function", "c"),
    ]
    cur.executemany(
        "INSERT INTO nodes(id, name, qualified_name, file_path, start_line, kind, language) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        nodes,
    )
    conn.commit()

    # Call the function under test.
    result = _node_fqn_map(cur, ["c"])

    # Build expected (spec-correct) FQNs manually.
    # Replicate _fqn_for logic: path components joined by "::", extension→hyphen.
    # file_path = "src/util.c" → "src::util-c" prefix
    suffix_free = _fqn_for("src/util.c", "helper")
    with_suffix_2 = _fqn_for("src/util.c", "helper_2")
    with_suffix_3 = _fqn_for("src/util.c", "helper_3")

    expected = {
        1: suffix_free,
        2: with_suffix_2,
        3: with_suffix_3,
    }

    # Check if the actual output matches the buggy (0-based) pattern.
    buggy_suffix_1 = _fqn_for("src/util.c", "helper_1")
    buggy_suffix_2 = _fqn_for("src/util.c", "helper_2")

    buggy_expected = {
        1: suffix_free,
        2: buggy_suffix_1,
        3: buggy_suffix_2,
    }

    # Classification: bug confirmed if actual != spec-correct AND actual == buggy.
    match_spec = result == expected
    match_buggy = result == buggy_expected

    if not match_spec and match_buggy:
        print("CONFIRMED — off-by-one deduplication suffix reproduced.")
        print(f"  Expected (spec-correct): {expected}")
        print(f"  Actual (buggy):          {result}")
        print(f"  Buggy pattern matches:   {match_buggy}")
    elif not match_spec:
        print("CONFIRMED — actual does not match spec (though buggy pattern also mismatched)")
        print(f"  Expected (spec):  {expected}")
        print(f"  Actual:           {result}")
        print(f"  Buggy expected:   {buggy_expected}")
    else:
        print("NOT CONFIRMED — actual output matched spec-correct output")
        print(f"  Result: {result}")

    conn.close()

if __name__ == "__main__":
    try:
        run_test()
    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)

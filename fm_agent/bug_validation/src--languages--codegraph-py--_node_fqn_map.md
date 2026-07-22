# Bug Report: _node_fqn_map

**Source file:** `/tmp/fm_agent_wt_FM-Agent_xyeqtgt6/snapshot/fm_agent/extracted_functions/src/languages/codegraph-py/_node_fqn_map.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- Returns a dict mapping each node's id to its fully-qualified function
    name (FQN)
  - The mapping includes exactly the rows from the nodes table whose kind
    is either 'function' or 'method' and whose language is one of the given
    cg_langs values, ordered by (file_path ASC, start_line ASC)
  - Each FQN is derived from the node's file_path and a canonicalized,
    deduplicated function name in the canonical convention where path
    components are joined by "::" and the source file extension in the
    parent directory component is replaced by a hyphen
  - Function name canonicalization strips angle-bracket template parameters
    and normalizes operator-overload names to safe identifier forms
  - When N > 1 nodes share the same file_path and canonicalized name, the
    first such node in the result ordering receives the canonicalized name
    without a suffix, and each subsequent node (k-th, 1-indexed) receives
    the canonicalized name suffixed with _k
  - Returns an empty dict when the query matches no rows
  - The deduplication rule and ordering correspond to those used by
    get_functions_by_file, ensuring that the FQN assigned to a node here
    matches the FQN the extracted function file receives for the same node

---

### Actual Behavior

If no exception occurs: The function returns a dictionary `result` such that: Let `Q` be the ordered list of rows from `cur.execute` of `SELECT id, name, qualified_name, file_path, start_line FROM nodes WHERE kind IN ('function','method') AND language IN (?,...,?)` with parameters `cg_langs`, sorted by `file_path, start_line` ascending. For each row `(id, name, qualified_name, file_path, _)` in `Q` in order, let `ident = _extraction_ident(name, qualified_name)` and `key = (file_path, ident)`. Define a counter function `occ(key, i) = |{ j < i | key_j = key }|` (the 0based occurrence index). Then `deduped = ident if occ(key, i) = 0 else f"{ident}_{occ(key,i)}"`. Then `result[id] = _fqn_for(file_path, deduped)`. After iterating all rows, `result` contains exactly `{r.id for r in Q}` as keys and no other entries. The cursor `cur` has been completely fetched (no remaining rows from that query). No other mutable state is modified. If an exception is raised (e.g., SQL error, fetch error, or exceptions from helper functions), the exception propagates; no explicit rollback or cleanup is performed, and the state of `cur` and any partially built `result` is lost to the caller.

---

## Code Evidence

Line 26: deduped = ident if c == 0 else f"{ident}_{c}"

---

## Trigger Condition

The specification requires the k-th occurrence (1indexed) to be suffixed with _k, whereas the code uses a zerobased counter that produces _1 for the second occurrence, _2 for the third, etc., violating the defined deduplication rule.

---

## How to trigger the bug

The bug is an off-by-one error in the deduplication suffix assignment. When N > 1 nodes share the same `(file_path, ident)` key, the code uses a 0-based counter `c` directly as the suffix, producing `_1` for the second occurrence instead of `_2` (per the 1-indexed spec requirement), `_2` for the third instead of `_3`, and so on.

### Inputs

| Parameter | Value |
|-----------|-------|
| `cur` | SQLite cursor on an in-memory DB with a `nodes` table containing three rows all with `file_path='src/util.c'`, `name='helper'`, `kind='function'`, `language='c'`, ordered by `start_line` ascending |
| `cg_langs` | `["c"]` |

### Expected (spec-correct) Output

`{1: 'src::util-c::helper', 2: 'src::util-c::helper_2', 3: 'src::util-c::helper_3'}`

### Actual (buggy) Output

`{1: 'src::util-c::helper', 2: 'src::util-c::helper_1', 3: 'src::util-c::helper_2'}`

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import sqlite3
import sys
sys.path.insert(0, "src")

from languages.codegraph import _node_fqn_map

conn = sqlite3.connect(":memory:")
cur = conn.cursor()
cur.execute("""
    CREATE TABLE nodes (
        id INTEGER PRIMARY KEY, name TEXT, qualified_name TEXT,
        file_path TEXT, start_line INTEGER, kind TEXT, language TEXT
    )
""")
cur.executemany(
    "INSERT INTO nodes VALUES (?, ?, ?, ?, ?, ?, ?)",
    [(1, "helper", "helper", "src/util.c", 10, "function", "c"),
     (2, "helper", "helper", "src/util.c", 50, "function", "c"),
     (3, "helper", "helper", "src/util.c", 90, "function", "c")],
)
conn.commit()

result = _node_fqn_map(cur, ["c"])
print(result)
# actual (buggy) output: {1: 'src::util-c::helper', 2: 'src::util-c::helper_1', 3: 'src::util-c::helper_2'}
# expected (correct) output: {1: 'src::util-c::helper', 2: 'src::util-c::helper_2', 3: 'src::util-c::helper_3'}
```

---

## Probe Script

```python
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
```

### Probe Output

```
CONFIRMED — off-by-one deduplication suffix reproduced.
  Expected (spec-correct): {1: 'src::util-c::helper', 2: 'src::util-c::helper_2', 3: 'src::util-c::helper_3'}
  Actual (buggy):          {1: 'src::util-c::helper', 2: 'src::util-c::helper_1', 3: 'src::util-c::helper_2'}
  Buggy pattern matches:   True
```

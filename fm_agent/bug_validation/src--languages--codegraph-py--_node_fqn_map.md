# Bug Report: _node_fqn_map

**Source file:** `/tmp/fm_agent_wt_FM-Agent_dlsr6ukl/snapshot/fm_agent/extracted_functions/src/languages/codegraph-py/_node_fqn_map.py`
**Verdict:** MISMATCH
**Confirmation status:** not_confirmed

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

After successful execution, the function returns a dictionary `result` mapping each node id (integer) of all rows in the `nodes` table where `kind` is either 'function' or 'method' and `language` is one of the languages in the nonempty sequence `cg_langs`, to a fully qualified name string. The FQN is constructed by processing the rows in the order given by `ORDER BY file_path, start_line`. For each row, a bare function name is extracted by stripping any anglebracket template parameters from `name`, then canonicalized into a safe identifier (`cname`). For each distinct `(file_path, cname)` pair, the first occurrence (by the ordering) receives `cname` as the deduplicated name; subsequent occurrences receive `cname_1`, `cname_2`, etc., where the appended number is the count of prior occurrences of that pair. The FQN is then formed by calling `_fqn_for(file_path, deduped_name)`, which combines the file path and the deduplicated name using `::` as separator and normalizes directory separators. The returned dictionary contains exactly one entry per matched node; its size equals the number of rows selected by the query. The cursor's result set is exhausted, but the database is not modified. Formal logic: Let Q be the sequence of tuples (id, name, file_path, start_line) obtained from `SELECT id, name, file_path, start_line FROM nodes WHERE kind IN ('function','method') AND language IN (placeholders) ORDER BY file_path, start_line`, with placeholders bound to `cg_langs`. Let `counts` be an initially empty map from `(file_path, cname)` to integer counts. After processing Q in order, the returned dictionary M satisfies: M = { id_j : [ let bare_j = _bare_function_name(name_j); cname_j = canonicalize(bare_j); key_j = (file_path_j, cname_j); c_j = counts.get(key_j, 0); deduped_j = cname_j if c_j == 0 else f"{cname_j}_{c_j}"; fqn_j = _fqn_for(file_path_j, deduped_j); counts[key_j] := c_j + 1; yield (id_j, fqn_j) ] for each j in 1..|Q| }.

---

## Code Evidence

Line 9: placeholders = ",".join("?" * len(cg_langs))
Line 10: cur.execute(

---

## Trigger Condition

The specification explicitly requires returning an empty dict when the query matches no rows. With an empty cg_langs, the query matches no rows and the specification thus demands an empty dict. The code, however, generates an SQL clause `language IN ()` which is syntactically invalid, causing a database error and preventing the function from returning any value.

---

## How to trigger the bug

The trigger condition claims that passing an empty `cg_langs` list to `_node_fqn_map` generates invalid SQL (`language IN ()`) and raises a database error. However, **SQLite treats `IN ()` as matching zero rows**, not as a syntax error. Therefore the function executes successfully: no rows match, `cur.fetchall()` returns an empty list, the loop body never executes, and the function returns `{}` — which is exactly what the specification requires.

### Inputs

| Parameter | Value |
|-----------|-------|
| `cur` | SQLite cursor connected to an in-memory database with a `nodes` table |
| `cg_langs` | `[]` (empty list) |

### Expected (spec-correct) Output

`{}` (empty dict — the query matches no rows)

### Actual (buggy) Output

`{}` (empty dict — SQLite's `IN ()` returns 0 rows, the function returns the unmodified result dict)

### How to Reproduce

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import sqlite3
from src.languages.codegraph import _node_fqn_map

conn = sqlite3.connect(":memory:")
cur = conn.cursor()
cur.execute("CREATE TABLE nodes (id, name, file_path, start_line, kind, language)")
cur.execute("INSERT INTO nodes VALUES (1, 'foo', '/a/b.py', 10, 'function', 'python')")
conn.commit()

result = _node_fqn_map(cur, [])
# actual (buggy) output: {}
# expected (correct) output: {}
```

---

## Probe Script

```python
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
```

### Probe Output

```
NOT CONFIRMED — _node_fqn_map returned empty dict as spec requires
  actual: {}  expected: {}
  SQLite treats IN () as matching 0 rows (not a syntax error)
```

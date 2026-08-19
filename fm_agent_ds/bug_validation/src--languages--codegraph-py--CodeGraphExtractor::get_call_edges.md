# Bug Report: CodeGraphExtractor::get_call_edges

**Source file:** `/home/fancy/Projects_Vault/FM-Agent/fm_agent/extracted_functions/src/languages/codegraph-py/CodeGraphExtractor::get_call_edges.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

Returns a dict mapping each caller FQN (str) to a non-empty set of callee FQNs (set[str]) for all direct call relationships discovered in source files of the given language within the indexed project. Both keys and values use canonicalized FQNs with :: as the component separator. Call edges include both function-call edges and constructor invocations synthesized from class-instantiation relationships. FQN identity is resolved by codegraph node ID, preserving the precise caller/callee association for same-named functions in different files. Returns an empty dict when lang_key is not a recognized language or when no call edges exist for the given language.

---

### Actual Behavior

If no exception is raised, then: If the lookup _CG_LANG.get(lang_key) yields a non-empty list cg_langs, then the method opens a connection to self._db, obtains a cursor, computes fqn_of = _node_fqn_map(cur, cg_langs), then constructs a mapping result where for each (src, tgt) from edges.kind='calls' with source language in cg_langs, if both fqn_of[src] and fqn_of[tgt] are not None, then result[fqn_of[src]] contains fqn_of[tgt]; additionally if a ctor_filter = _CONSTRUCTOR_FILTER.get(lang_key) exists, for each (src, ctor_id) from the second query (edges.kind='instantiates' with source language in cg_langs, target class containing a method/function matching ctor_filter), if both fqn_of[src] and fqn_of[ctor_id] are not None, then result[fqn_of[src]] contains fqn_of[ctor_id]. The connection is closed before return. The method returns dict(result). If _CG_LANG.get(lang_key) yields a falsy value, the method returns {} without any side effects. In all cases, self remains unmodified, self._db is unchanged, no resources leaked.

---

## Code Evidence

Line 40:             caller, callee = fqn_of.get(src_id), fqn_of.get(tgt_id)
Line 41:             if caller and callee:
Line 42:                 result[caller].add(callee)

---

## Trigger Condition

The code omits call edges where the callee's FQN is not present in fqn_of, which only covers nodes of the requested languages. However, the specification demands all direct call relationships discovered in source files of the given language, including calls to functions defined in other languages. This leads to a missing callee in the output dict.

---

## How to trigger the bug

When a function in the requested language calls a function in a different language, the callee's node ID is not present in `fqn_of` (which `_node_fqn_map` populates only for nodes whose `language` column matches `cg_langs`). The guard `if caller and callee` at line 41 evaluates to `False` because `callee` is `None`, and the edge is silently dropped from the result dict.

In a multi-language project where Python code calls C functions (e.g., via FFI), or where TypeScript calls JavaScript functions, the call edges from the requested language to the other language are lost.

### Inputs

| Parameter | Value |
|-----------|-------|
| `lang_key` | `"python"` |
| Database contents | One Python function node (`py_func` at `src/py_code.py`), one C function node (`c_func` at `src/c_code.c`), one `calls` edge from the Python node to the C node |

### Expected (spec-correct) Output

`{"src::py_code-py::py_func": {"src::c_code-c::c_func"}}`

### Actual (buggy) Output

`{}`

### How to Reproduce

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import sqlite3
import tempfile
import os
import time
from src.languages.codegraph import CodeGraphExtractor

with tempfile.TemporaryDirectory() as tmpdir:
    codegraph_dir = os.path.join(tmpdir, ".codegraph")
    os.makedirs(codegraph_dir)
    db_path = os.path.join(codegraph_dir, "codegraph.db")
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.executescript("""
        CREATE TABLE nodes (id TEXT PRIMARY KEY, kind TEXT, name TEXT,
            qualified_name TEXT, file_path TEXT, language TEXT,
            start_line INT, end_line INT, start_column INT, end_column INT,
            updated_at INT);
        CREATE TABLE edges (id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT, target TEXT, kind TEXT,
            FOREIGN KEY (source) REFERENCES nodes(id),
            FOREIGN KEY (target) REFERENCES nodes(id));
    """)
    now = int(time.time() * 1000)
    cur.execute("INSERT INTO nodes VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        ("n1", "function", "py_func", "py_func", "src/py_code.py",
         "python", 1, 5, 0, 19, now))
    cur.execute("INSERT INTO nodes VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        ("n2", "function", "c_func", "c_func", "src/c_code.c",
         "c", 1, 5, 0, 19, now))
    cur.execute("INSERT INTO edges (source, target, kind) VALUES (?,?,?)",
        ("n1", "n2", "calls"))
    conn.commit(); conn.close()
    extractor = CodeGraphExtractor(db_path)
    actual = extractor.get_call_edges("python")
    print(actual)
// actual (buggy) output: {}
// expected (correct) output: {'src::py_code-py::py_func': {'src::c_code-c::c_func'}}
```

---

## Probe Script

```python
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
```

### Probe Output

```
CONFIRMED — Bug reproduced in attempt 1: cross-language call edge from Python to C was dropped. actual={} | expected={'src::py_code-py::py_func': {'src::c_code-c::c_func'}}
```

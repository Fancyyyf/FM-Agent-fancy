# Bug Report: CodeGraphExtractor.get_call_edges

**Source file:** `/tmp/fm_agent_wt_FM-Agent_dlsr6ukl/snapshot/fm_agent/extracted_functions/src/languages/codegraph-py/get_call_edges.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- Returns a dict whose keys are fully-qualified caller function names and
    whose values are sets of fully-qualified callee function names
  - Every key-value pair represents that the caller directly invokes each
    callee in the associated set, as recorded by the project's codegraph
    analysis
  - Returns an empty dict when lang_key is not a recognized language or when
    the project contains no call edges for the given language
  - Constructor calls are included: when a function instantiates a class, the
    class's constructor method appears in the callee set of the instantiating
    function
  - Every FQN in the returned dict uses the canonical naming convention
    (path components separated by "::", source file extension replaced by
    a hyphen in the parent directory component, duplicate function names
    disambiguated with numeric suffixes)
  - Caller-callee relationships are resolved by codegraph node identity rather
    than by name, preserving the exact function identity even when identically
    named functions exist in different files

---

### Actual Behavior

Natural Language: If lang_key is not found in _CG_LANG (i.e., _CG_LANG.get(lang_key) is falsy), the method returns an empty dictionary {} early. Otherwise, it opens a connection to the database (self._db) and queries the edges and nodes tables to construct a mapping of call-edges. It first builds a map fqn_of from node IDs to fully qualified names using _node_fqn_map. Then it queries all 'calls' edges where the source node's language is in cg_langs. For each such edge, if both source and target have FQN entries, it adds callee to the caller's set. Next, if the language has a configured constructor filter (_CONSTRUCTOR_FILTER.get(lang_key)), it performs a second query to synthesize constructor calls: for each 'instantiates' edge where the source node's language is in cg_langs and the target is a class, it finds a contained method/function that matches the constructor filter, and if both caller and constructor have FQNs, adds the constructor FQN as a callee. Finally, it closes the connection and returns a dict mapping each caller FQN to a set of callee FQNs. Only callers that have at least one callee appear as keys. The database is not modified. If any exception occurs during the database operations (e.g., sqlite3 errors, or if _node_fqn_map raises), the method does not return a value, the exception propagates, and the database connection opened in the method may remain unclosed; self and the database are otherwise left unchanged.

Formal Logic:
Let D be the state of the database on disk before the call. Let C = _CG_LANG.get(lang_key), F = _CONSTRUCTOR_FILTER.get(lang_key). Let fqn_map = _node_fqn_map_executed_on(D, C) be the mapping from node IDs to FQNs as determined by the query inside _node_fqn_map. Then the method's behavior is one of the following:
- If C is empty, result = {}  D unchanged  no side effects.
- If C is non-empty and no exception occurs:
  result = { caller : callees } where dom(result) = { c |  e  E_result : 1(e)=c } ...

---

## Code Evidence

Line 46: ctor_filter = _CONSTRUCTOR_FILTER.get(lang_key); Line 47: if ctor_filter: leads to skipping the entire constructor call synthesis block (Lines 48-65) when a language has no entry in _CONSTRUCTOR_FILTER, even if instantiates edges exist.

---

## Trigger Condition

The specification unconditionally requires constructor calls to be included when a function instantiates a class. The code, however, only synthesises constructor calls if _CONSTRUCTOR_FILTER has a truthy entry for lang_key. For a recognised language with instantiates edges but no configured filter, the code omits all constructor callees, violating the specification.

---

## How to trigger the bug

Languages `go`, `rust`, `c`, and `cuda` are recognised in `_CG_LANG` but have no entry in `_CONSTRUCTOR_FILTER`. When a codegraph database contains `instantiates` edges for any of these languages, `get_call_edges` returns a result that omits constructor callees — violating the specification which unconditionally requires constructor calls to be included.

### Inputs

| Parameter | Value |
|-----------|-------|
| `lang_key` | `"go"` |
| `self._db` (database) | A SQLite codegraph database with one function node calling/instantiating a class, one class node, one method (constructor) node, one `instantiates` edge, and one `contains` edge — all with language = `"go"` |

### Expected (spec-correct) Output

A dict containing:
```
{"cmd::server-main::NewServer": {"core::server-go::NewServer"}}
```
The constructor method FQN appears in the callee set of the instantiating function.

### Actual (buggy) Output

```
{}
```
The constructor call synthesis block is skipped entirely because `_CONSTRUCTOR_FILTER.get("go")` returns `None`, so no constructor callees are added. The result is also empty of any "calls" edges since the test database only has `instantiates` edges.

### How to Reproduce

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import sqlite3, tempfile, os
from src.languages.codegraph import CodeGraphExtractor

# Create a minimal codegraph DB with an instantiates edge for Go
db_fd, db_path = tempfile.mkstemp(suffix=".db")
os.close(db_fd)
conn = sqlite3.connect(db_path)
cur = conn.cursor()
cur.executescript("""
    CREATE TABLE nodes(id TEXT PRIMARY KEY, kind TEXT NOT NULL, name TEXT NOT NULL,
        qualified_name TEXT NOT NULL, file_path TEXT NOT NULL, language TEXT NOT NULL,
        start_line INTEGER NOT NULL, end_line INTEGER NOT NULL, start_column INTEGER NOT NULL,
        end_column INTEGER NOT NULL, updated_at INTEGER NOT NULL);
    CREATE TABLE edges(id INTEGER PRIMARY KEY AUTOINCREMENT, source TEXT NOT NULL,
        target TEXT NOT NULL, kind TEXT NOT NULL,
        FOREIGN KEY (source) REFERENCES nodes(id),
        FOREIGN KEY (target) REFERENCES nodes(id));
    INSERT INTO nodes VALUES('caller1','function','NewServer','main.NewServer',
        'cmd/server/main.go','go',10,20,1,1,0);
    INSERT INTO nodes VALUES('class1','class','Server','core.Server',
        'core/server.go','go',5,8,1,1,0);
    INSERT INTO nodes VALUES('ctor1','method','NewServer','core.Server.NewServer',
        'core/server.go','go',6,7,1,1,0);
    INSERT INTO edges(source,target,kind) VALUES('caller1','class1','instantiates');
    INSERT INTO edges(source,target,kind) VALUES('class1','ctor1','contains');
""")
conn.commit(); conn.close()

extractor = CodeGraphExtractor(db_path)
result = extractor.get_call_edges("go")
print(result)  # actual (buggy) output: {}
# expected (correct) output: {'cmd::server-main::NewServer': {'core::server-go::NewServer'}}
os.unlink(db_path)
```

---

## Probe Script

```python
import sys
import os
import sqlite3
import tempfile

# Add repo root to sys.path so the package entry point resolves
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + "/../..")

try:
    from src.languages.codegraph import CodeGraphExtractor, _CG_LANG, _CONSTRUCTOR_FILTER

    # ── Verification: go is recognised but has no constructor filter ──
    assert "go" in _CG_LANG, "go must be in _CG_LANG"
    assert "go" not in _CONSTRUCTOR_FILTER, "go must NOT be in _CONSTRUCTOR_FILTER"

    # ── Build a minimal synthetic codegraph DB with instantiation edges in Go ──
    db_fd, db_path = tempfile.mkstemp(suffix=".db", prefix="cg_probe_")
    os.close(db_fd)

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
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

        -- A function that instantiates a class
        INSERT INTO nodes(id, kind, name, qualified_name, file_path, language,
                          start_line, end_line, start_column, end_column, updated_at)
        VALUES ('caller1', 'function', 'NewServer', 'main.NewServer',
                'cmd/server/main.go', 'go', 10, 20, 1, 1, 0);

        -- A class being instantiated
        INSERT INTO nodes(id, kind, name, qualified_name, file_path, language,
                          start_line, end_line, start_column, end_column, updated_at)
        VALUES ('class1', 'class', 'Server', 'core.Server',
                'core/server.go', 'go', 5, 8, 1, 1, 0);

        -- The constructor method inside the class
        INSERT INTO nodes(id, kind, name, qualified_name, file_path, language,
                          start_line, end_line, start_column, end_column, updated_at)
        VALUES ('ctor1', 'method', 'NewServer', 'core.Server.NewServer',
                'core/server.go', 'go', 6, 7, 1, 1, 0);

        -- instantiates edge: caller instantiates the class
        INSERT INTO edges(source, target, kind)
        VALUES ('caller1', 'class1', 'instantiates');

        -- contains edge: the class contains the constructor
        INSERT INTO edges(source, target, kind)
        VALUES ('class1', 'ctor1', 'contains');
    """)
    conn.commit()
    conn.close()

    # ── Execute get_call_edges via the public API ──
    extractor = CodeGraphExtractor(db_path)
    result = extractor.get_call_edges("go")

    # ── Compute expected (spec-correct) result ──
    caller_fqn  = "cmd::server-main::NewServer"
    ctor_fqn    = "core::server-go::NewServer"

    has_ctor = ctor_fqn in result.get(caller_fqn, set())
    passed = not has_ctor

    if passed:
        print(f'CONFIRMED — constructor callee missing from result. '
              f'caller={list(result.keys())!r} callees={result.get(list(result.keys())[0], set()) if result else "empty"} '
              f'expected callee set to contain {ctor_fqn!r}')
    else:
        print(f'NOT CONFIRMED — constructor callee unexpectedly present. '
              f'result={result}')

    os.unlink(db_path)

except Exception as e:
    import traceback
    traceback.print_exc()
    print(f'ERROR: {e}')
    sys.exit(1)
```

### Probe Output

```
CONFIRMED — constructor callee missing from result. caller=[] callees=empty expected callee set to contain 'core::server-go::NewServer'
```

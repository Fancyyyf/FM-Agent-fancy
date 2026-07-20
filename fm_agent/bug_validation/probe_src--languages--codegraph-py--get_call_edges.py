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
    # The spec says constructor callees MUST be included when a function
    # instantiates a class.  For Go, the constructor method should appear in
    # the callee set of the instantiating function.
    # The FQN format is: dir::file-ext::name, e.g.:
    #   cmd::server-main::NewServer (caller)
    #   core::server-go::NewServer (constructor callee)
    caller_fqn  = "cmd::server-main::NewServer"
    ctor_fqn    = "core::server-go::NewServer"

    # Check whether the constructor callee is present
    has_ctor = ctor_fqn in result.get(caller_fqn, set())

    # Spec requires: constructor must be in the callee set
    # Bug behaviour: constructor is NOT in the callee set (because _CONSTRUCTOR_FILTER
    #                has no entry for "go", so the synthesis block is skipped)
    # passed = True means the bug is reproduced (actual output is wrong per spec)
    passed = not has_ctor

    if passed:
        print(f'CONFIRMED — constructor callee missing from result. '
              f'caller={list(result.keys())!r} callees={result.get(list(result.keys())[0], set()) if result else "empty"} '
              f'expected callee set to contain {ctor_fqn!r}')
    else:
        print(f'NOT CONFIRMED — constructor callee unexpectedly present. '
              f'result={result}')

    # Cleanup
    os.unlink(db_path)

except Exception as e:
    import traceback
    traceback.print_exc()
    print(f'ERROR: {e}')
    sys.exit(1)

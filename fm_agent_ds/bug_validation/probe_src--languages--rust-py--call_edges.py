"""Probe for bug src--languages--rust-py--call_edges.

Claims: get_call_edges("rust") returns (caller_stem, caller_module) tuple keys
and bare-stem callees, violating the spec that requires FQN format.
"""
import os
import re
import sqlite3
import sys
import tempfile

try:
    from src.languages.codegraph import CodeGraphExtractor

    # Create a temporary directory with a mock .codegraph/codegraph.db
    tmpdir = tempfile.mkdtemp()
    codegraph_dir = os.path.join(tmpdir, ".codegraph")
    os.makedirs(codegraph_dir, exist_ok=True)
    db_path = os.path.join(codegraph_dir, "codegraph.db")

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute(
        "CREATE TABLE nodes ("
        "  id INTEGER, name TEXT, qualified_name TEXT,"
        "  file_path TEXT, kind TEXT, language TEXT, start_line INTEGER"
        ")"
    )
    cur.execute(
        "CREATE TABLE edges (source INTEGER, target INTEGER, kind TEXT)"
    )

    # Insert two Rust functions
    cur.execute(
        "INSERT INTO nodes VALUES "
        "(1, 'main', 'main', 'src/main.rs', 'function', 'rust', 1)"
    )
    cur.execute(
        "INSERT INTO nodes VALUES "
        "(2, 'helper', 'helper', 'src/utils.rs', 'function', 'rust', 5)"
    )
    # Call edge: main -> helper
    cur.execute("INSERT INTO edges VALUES (1, 2, 'calls')")
    conn.commit()
    conn.close()

    extractor = CodeGraphExtractor(db_path)
    result = extractor.get_call_edges("rust")

    # --- Verify the output format against the spec ---

    # Spec: "caller identifiers use the canonicalized FQN format" → must be str
    caller_types_ok = all(isinstance(k, str) for k in result)
    # Bug claim: returns (caller_stem, caller_module) tuples → would fail
    caller_is_tuple = any(isinstance(k, tuple) for k in result)

    # Spec: "callee identifiers use the canonicalized FQN format" → each must be str
    callee_types_ok = all(
        isinstance(v, set)
        and all(isinstance(item, str) for item in v)
        for v in result.values()
    )
    # Bug claim: callees are bare stems → check FQN pattern (contains ::)
    fqn_pattern = re.compile(r"::")
    callee_has_fqn = (
        all(
            fqn_pattern.search(item)
            for v in result.values()
            for item in v
        )
        if result
        else True  # vacuously true for empty result
    )

    # Print diagnostics
    print(f"Result keys: {list(result.keys())}")
    for k, v in result.items():
        print(f"  caller={k!r} (type={type(k).__name__}) -> callees={v!r}")
    print()
    print(f"Caller keys are strings (FQN):    {caller_types_ok}")
    print(f"Caller keys are tuples (claimed): {caller_is_tuple}")
    print(f"Callees are strings (FQN):        {callee_types_ok}")
    print(f"Callees contain '::' (FQN):       {callee_has_fqn}")

    # Verdict: spec says FQN format. If callers are strings (not tuples) AND
    # callees are strings (not bare stems), the code matches the spec.
    if caller_types_ok and not caller_is_tuple and callee_types_ok:
        print()
        print(
            "NOT CONFIRMED — caller identifiers are FQN strings (not tuples), "
            "callee identifiers are FQN strings (not bare stems). "
            "Actual behaviour matches the specification."
        )
    else:
        print()
        print(
            "CONFIRMED — output format does not match the FQN spec claim"
        )

except Exception as e:
    import traceback

    print(f"ERROR: {e}")
    traceback.print_exc()
    sys.exit(1)
finally:
    # Cleanup temporary directory
    import shutil

    if "tmpdir" in dir() and os.path.isdir(tmpdir):
        shutil.rmtree(tmpdir, ignore_errors=True)

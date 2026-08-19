import os
import sqlite3
import sys
import tempfile


def main():
    """Probe: verify call_edges key format is strings, not tuples.

    The spec requires keys as canonicalized ::-separated FQN strings.
    The trigger_condition claims keys are returned as tuples.
    """
    repo_root = os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    )
    sys.path.insert(0, repo_root)

    try:
        from src.languages.go import call_edges
    except Exception as e:
        print(f"ERROR: cannot import call_edges — {e}")
        sys.exit(1)

    # Create a temp directory with a minimal codegraph SQLite DB.
    tmpdir = tempfile.mkdtemp(prefix="probe_go_call_edges_")
    cg_dir = os.path.join(tmpdir, ".codegraph")
    os.makedirs(cg_dir, exist_ok=True)
    db_path = os.path.join(cg_dir, "codegraph.db")

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # Minimal codegraph schema.
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS nodes (
            id INTEGER PRIMARY KEY,
            name TEXT,
            qualified_name TEXT,
            file_path TEXT,
            start_line INTEGER,
            end_line INTEGER,
            kind TEXT,
            language TEXT
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS edges (
            source INTEGER,
            target INTEGER,
            kind TEXT
        )
        """
    )

    # Insert a caller (Go function) and a callee.
    cur.execute(
        "INSERT INTO nodes VALUES (1, 'main', 'main.main', 'main.go', 1, 10, 'function', 'go')"
    )
    cur.execute(
        "INSERT INTO nodes VALUES (2, 'helper', 'main.helper', 'main.go', 12, 15, 'function', 'go')"
    )
    cur.execute("INSERT INTO edges VALUES (1, 2, 'calls')")
    conn.commit()
    conn.close()

    # Call the function under test.
    try:
        result = call_edges(tmpdir)
    except Exception as e:
        print(f"ERROR: call_edges raised — {type(e).__name__}: {e}")
        sys.exit(1)

    if result is None:
        print("ERROR: call_edges returned None (codegraph DB was not detected)")
        sys.exit(1)

    if not isinstance(result, dict):
        print(
            f"NOT CONFIRMED — unexpected return type: {type(result).__name__}, "
            "expected a dict"
        )
        return

    # Check key types.
    keys_are_strings = all(isinstance(k, str) for k in result)
    keys_are_tuples = any(isinstance(k, tuple) for k in result)

    spec_claim = (
        "keys are canonicalized caller FQNs using :: as namespace separator"
    )

    if keys_are_strings:
        # Verify the strings actually contain :: separators (FQN format)
        fqn_like = any("::" in k for k in result)
        print(
            f"NOT CONFIRMED — keys are strings ({list(result.keys())}), "
            f"::-separated FQN format present: {fqn_like}. "
            f"This matches the spec ({spec_claim}), "
            f"not the claimed bug (tuple keys)."
        )
    elif keys_are_tuples:
        print(
            f"CONFIRMED — keys are tuples: {list(result.keys())!r}. "
            f"Spec requires {spec_claim}."
        )
    else:
        print(
            f"NOT CONFIRMED — unexpected key type(s): "
            f"{[type(k).__name__ for k in result.keys()]}"
        )

    # Cleanup tempdir.
    import shutil
    shutil.rmtree(tmpdir, ignore_errors=True)


if __name__ == "__main__":
    main()

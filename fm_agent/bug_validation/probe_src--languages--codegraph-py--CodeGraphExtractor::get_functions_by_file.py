import os
import sys
import sqlite3
import tempfile
import shutil

# Add repo root to Python path so `from src.languages.codegraph import ...` works
repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, repo_root)

try:
    from src.languages.codegraph import CodeGraphExtractor

    # --- Setup: create a temporary directory with test fixtures ---
    tmpdir = tempfile.mkdtemp(prefix="probe_cg_")
    cg_dir = os.path.join(tmpdir, ".codegraph")
    os.makedirs(cg_dir, exist_ok=True)
    db_path = os.path.join(cg_dir, "codegraph.db")

    # Create the codegraph SQLite database with the nodes table
    conn = sqlite3.connect(db_path)
    conn.execute("""
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
    """)

    # Create a small Python source file as a test subject
    test_src = os.path.join(tmpdir, "test_module.py")
    with open(test_src, "w") as f:
        f.write("def hello():\n    return 'world'\n\n")
        f.write("def goodbye():\n    return 'farewell'\n")

    # Insert function entries referencing the test source file
    conn.execute(
        "INSERT INTO nodes (name, qualified_name, file_path, start_line, end_line, kind, language) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        ("hello", "hello", "test_module.py", 1, 2, "function", "python"),
    )
    conn.execute(
        "INSERT INTO nodes (name, qualified_name, file_path, start_line, end_line, kind, language) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        ("goodbye", "goodbye", "test_module.py", 4, 5, "function", "python"),
    )
    conn.commit()
    conn.close()

    # --- Test: call get_functions_by_file with a RELATIVE proj_dir ---
    cwd = os.getcwd()
    rel_proj_dir = os.path.relpath(tmpdir, cwd)

    extractor = CodeGraphExtractor(db_path)
    result = extractor.get_functions_by_file("python", proj_dir=rel_proj_dir)

    # --- Oracle: spec requires ALL keys to be absolute filesystem paths ---
    bug_confirmed = False
    non_absolute_keys = []

    for key in result:
        if not os.path.isabs(key):
            non_absolute_keys.append(key)
            bug_confirmed = True

    expected = os.path.abspath(os.path.join(rel_proj_dir, "test_module.py"))

    if bug_confirmed:
        print(
            f"CONFIRMED — spec requires absolute paths as dict keys, "
            f"but passing a relative proj_dir={rel_proj_dir!r} produced "
            f"relative key: {non_absolute_keys!r} instead of expected absolute key {expected!r}"
        )
    else:
        print(f"NOT CONFIRMED — all keys are absolute: {list(result.keys())!r}")

except Exception as e:
    import traceback
    print(f"ERROR: {e}")
    traceback.print_exc()
    sys.exit(1)
finally:
    if "tmpdir" in dir():
        shutil.rmtree(tmpdir, ignore_errors=True)

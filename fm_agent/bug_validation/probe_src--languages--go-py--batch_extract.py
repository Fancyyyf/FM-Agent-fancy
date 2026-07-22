import os
import sys
import sqlite3
import tempfile
import shutil

# Add repo root to Python path so `from src.languages.go import batch_extract` works
repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, repo_root)

try:
    from src.languages.go import batch_extract

    # --- Setup: temporary workspace outside the active repo ---
    tmpdir = tempfile.mkdtemp(prefix="probe_batch_go_")

    # proj_dir is the project root we'll pass to batch_extract
    proj_dir = os.path.join(tmpdir, "project")
    os.makedirs(proj_dir, exist_ok=True)

    # Create .codegraph/codegraph.db inside proj_dir
    cg_dir = os.path.join(proj_dir, ".codegraph")
    os.makedirs(cg_dir, exist_ok=True)
    db_path = os.path.join(cg_dir, "codegraph.db")

    # Create minimal codegraph SQLite database with nodes table
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

    # Create a Go source file INSIDE proj_dir (should be in result per spec)
    inside_file_rel = "pkg/handler.go"
    inside_file_abs = os.path.join(proj_dir, inside_file_rel)
    os.makedirs(os.path.dirname(inside_file_abs), exist_ok=True)
    with open(inside_file_abs, "w") as f:
        f.write("package handler\n\nfunc Hello() string {\n    return \"hello\"\n}\n")

    # Create a Go source file OUTSIDE proj_dir (should NOT be in result per spec)
    outside_dir = os.path.join(tmpdir, "outside")
    os.makedirs(outside_dir, exist_ok=True)
    outside_file_abs = os.path.join(outside_dir, "evil.go")
    with open(outside_file_abs, "w") as f:
        f.write("package evil\n\nfunc Malicious() string {\n    return \"owned\"\n}\n")

    # Compute a relative path from proj_dir to the outside file that uses parent traversal
    outside_rel = os.path.relpath(outside_file_abs, proj_dir)
    # e.g. "../outside/evil.go"

    # Insert function entries into the codegraph DB
    conn.execute(
        "INSERT INTO nodes (name, qualified_name, file_path, start_line, end_line, kind, language) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        ("Hello", "Hello", inside_file_rel, 3, 3, "function", "go"),
    )
    conn.execute(
        "INSERT INTO nodes (name, qualified_name, file_path, start_line, end_line, kind, language) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        ("Malicious", "Malicious", outside_rel, 3, 3, "function", "go"),
    )
    conn.commit()
    conn.close()

    # --- Test: call batch_extract ---
    result = batch_extract(proj_dir)

    # --- Oracle: spec requires "Only .go source files within proj_dir are processed"
    #     so NO returned key should be outside proj_dir ---
    proj_abs = os.path.abspath(proj_dir)

    outside_keys = []
    inside_keys = []
    for key in result:
        key_abs = os.path.abspath(key)
        # Check whether the resolved key is actually under proj_dir (not path-injection)
        if os.path.commonpath([key_abs, proj_abs]) != proj_abs:
            outside_keys.append(key)
        else:
            inside_keys.append(key)

    if outside_keys:
        print(
            f"CONFIRMED — spec requires only files within proj_dir, "
            f"but returned keys include paths outside proj_dir: {outside_keys!r}. "
            f"Inside keys: {inside_keys!r}"
        )
    else:
        print(f"NOT CONFIRMED — all returned keys are within proj_dir: {list(result.keys())!r}")

except Exception as e:
    import traceback
    print(f"ERROR: {e}")
    traceback.print_exc()
    sys.exit(1)
finally:
    if "tmpdir" in dir():
        shutil.rmtree(tmpdir, ignore_errors=True)

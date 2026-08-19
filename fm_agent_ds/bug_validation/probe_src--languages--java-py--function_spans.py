"""Probe for bug: function_spans returns None when backend is available but
file is not in the codegraph index, violating the spec that None should only
mean "backend unavailable, use fallback."

Bug ID: src--languages--java-py--function_spans
"""

import os
import sqlite3
import sys
import tempfile
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

tmpdir = tempfile.mkdtemp(prefix="probe_function_spans_")

try:
    # --- Set up a fake project with a minimal codegraph.db ---
    codegraph_dir = os.path.join(tmpdir, ".codegraph")
    os.makedirs(codegraph_dir, exist_ok=True)
    db_path = os.path.join(codegraph_dir, "codegraph.db")

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
    conn.commit()
    conn.close()

    # --- Call function_spans with a Java file NOT in the index ---
    from src.languages.java import function_spans

    # Use a file path inside the temp dir so relpath works cleanly
    fake_java = os.path.join(tmpdir, "Nonexistent.java")

    result = function_spans(tmpdir, fake_java)

    # The codegraph.db exists → backend is available (cg is truthy).
    # get_function_spans("java", fake_java) returns None because the file is
    # not in the nodes table (no Java entries at all).
    #
    # Spec says: when backend is available, return a list.
    #            None ONLY means backend unavailable.
    # Bug: returns None when backend available but file not indexed.
    if result is None:
        print(
            "CONFIRMED — function_spans returned None even though "
            "CodeGraphExtractor was loaded (backend available). "
            "The spec requires a list when the backend is available; "
            "None should only mean 'backend unavailable, use fallback'."
        )
    elif isinstance(result, list):
        print(
            f"NOT CONFIRMED — function_spans returned a list: {result!r}. "
            "The function correctly returns a list when the backend is available."
        )
    else:
        print(
            f"NOT CONFIRMED — unexpected return type: {type(result).__name__}: {result!r}"
        )

except Exception as e:
    import traceback
    traceback.print_exc()
    print(f"ERROR: {e}")
    sys.exit(1)

finally:
    import shutil
    shutil.rmtree(tmpdir, ignore_errors=True)

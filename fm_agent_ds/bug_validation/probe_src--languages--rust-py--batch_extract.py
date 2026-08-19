"""Probe script for bug: src--languages--rust-py--batch_extract

The spec claims batch_extract returns a dict (empty on init failure, full mapping
on success). The actual code propagates exceptions from get_functions_by_file
instead of catching them and returning a dict.

Strategy: create a mock codegraph DB that exists on disk but is invalid SQLite,
causing get_functions_by_file to raise an exception.
"""
import sys
import os
import tempfile
import traceback

# Probe is at <repo>/fm_agent/bug_validation/probe_*.py
# Go up 3 levels to reach repo root
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _REPO_ROOT)

try:
    from src.languages.rust import batch_extract

    # Create a temp directory with an invalid .codegraph/codegraph.db
    with tempfile.TemporaryDirectory() as tmpdir:
        codegraph_dir = os.path.join(tmpdir, ".codegraph")
        os.makedirs(codegraph_dir)
        db_path = os.path.join(codegraph_dir, "codegraph.db")
        # Write something that is NOT a valid SQLite database
        with open(db_path, "w") as f:
            f.write("this is not a valid sqlite database file\n")

        raised = False
        try:
            actual = batch_extract(tmpdir)
        except Exception as e:
            raised = True
            print(f"CONFIRMED — batch_extract raised exception instead of returning a dict: {type(e).__name__}: {e}")

        if not raised:
            expected = {}
            if actual == expected:
                print(f"NOT CONFIRMED — actual matched expected: {actual!r}")
            else:
                print(f"NOT CONFIRMED — actual: {actual!r} | expected: {expected!r} (different, but no exception)")

except Exception as e:
    print(f"ERROR: {e}")
    traceback.print_exc()
    sys.exit(1)

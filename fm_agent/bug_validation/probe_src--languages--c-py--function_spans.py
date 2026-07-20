import os
import sys

# Resolve repo root from the probe's own location (two dirs up from fm_agent/bug_validation/)
repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

try:
    from src.languages.c import function_spans

    proj_dir = repo_root
    # A C filename guaranteed NOT to be in the codegraph index.
    # os.path.abspath works fine on non-existent paths — get_function_spans
    # only queries the SQLite DB, it never reads the file from disk.
    filepath = os.path.join(proj_dir, "_probe_unindexed.c")

    actual = function_spans(proj_dir, filepath)

    # Per spec: when codegraph can be initialized from proj_dir (cg is truthy),
    # the function must return a LIST — never None.  The spec permits None
    # ONLY when codegraph CANNOT be initialized.
    # An unindexed file should yield an empty list.
    expected = []

    passed = actual != expected

except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)

if passed:
    print(f"CONFIRMED — actual: {actual!r} | expected: {expected!r}")
else:
    print(f"NOT CONFIRMED — actual matched expected: {actual!r}")

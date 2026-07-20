import sys
import os
import tempfile
import shutil

# Ensure the repo root is on sys.path so we can import src.languages.codegraph
sys.path.insert(0, os.getcwd())

from src.languages.codegraph import CodeGraphExtractor

# Create a temporary directory with a .codegraph/codegraph.db that is
# NOT a valid SQLite database (just a plain text file).
temp_dir = tempfile.mkdtemp()
codegraph_dir = os.path.join(temp_dir, ".codegraph")
os.makedirs(codegraph_dir)
db_path = os.path.join(codegraph_dir, "codegraph.db")
with open(db_path, "w") as f:
    f.write("not a valid SQLite database\n")

actual = None
expected = None

try:
    actual = CodeGraphExtractor.from_proj_dir(temp_dir)
    # Specification claim: returns None when no codegraph database is found.
    # The bug: returns an instance when a non-database file named codegraph.db
    # exists at the expected path.
    expected = None
    passed = actual is not None
except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)
finally:
    shutil.rmtree(temp_dir, ignore_errors=True)

if passed:
    print(f"CONFIRMED — actual: {type(actual).__name__} instance | expected: {expected!r}")
else:
    print(f"NOT CONFIRMED — actual matched expected: {actual!r}")

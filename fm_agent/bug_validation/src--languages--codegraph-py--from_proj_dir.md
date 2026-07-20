# Bug Report: from_proj_dir

**Source file:** `src/languages/codegraph.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- Returns an initialized CodeGraphExtractor instance when a codegraph database
    exists within the project directory structure reachable from proj_dir
  - Returns None when no codegraph database is found in the project directory
    structure, indicating the codegraph backend is unavailable for the project
  - The returned instance is bound to the discovered database and is ready to
    serve query operations (get_call_edges, function_spans, batch_extract) against
    the project's indexed source files

---

### Actual Behavior

The method returns an instance of the class (initialized with a live connection to the codegraph database) if a file named 'codegraph.db' exists under the '.codegraph' subdirectory of either `proj_dir` itself or its parent directory (obtained via `os.path.abspath` then `os.path.dirname`), checking `proj_dir` first. If neither directory contains that file, the method returns `None`. The returned instance, if any, is ready to resolve function definitions and call edges for all indexed languages. Formally, given the file system state FS at call time, define candidate_dirs = [proj_dir, dirname(abspath(proj_dir))] and for each candidate c let db_path(c) = join(c, '.codegraph', 'codegraph.db'). The result is cls(db_path(candidate_dirs[0])) if FS.exists(db_path(candidate_dirs[0])), else cls(db_path(candidate_dirs[1])) if FS.exists(db_path(candidate_dirs[1])), else None. The `proj_dir` argument is not mutated.

---

## Code Evidence

Line 9: if os.path.exists(db_path):
Line 10: return cls(db_path)

---

## Trigger Condition

The code returns a CodeGraphExtractor instance whenever the file exists, even if the file is not a valid codegraph database. The specification requires returning an initialized instance only when a codegraph database exists and returning None otherwise. The presence of a nondatabase file triggers a false positive, producing a broken instance that violates the postcondition.

---

## How to trigger the bug

The bug is triggered by placing a non-SQLite file at `.codegraph/codegraph.db` under a directory. The method treats any file named `codegraph.db` as a valid codegraph database without verifying the file is actually a valid SQLite database with the expected schema. The returned instance will fail with a SQLite error when any query method (e.g., `get_functions_by_file`, `get_call_edges`) is called.

### Inputs

| Parameter | Value |
|-----------|-------|
| proj_dir | A temp directory containing `.codegraph/codegraph.db` as a plain text file (not a valid SQLite database) |

### Expected (spec-correct) Output

`None` — because no valid codegraph database exists in the project directory structure.

### Actual (buggy) Output

A `CodeGraphExtractor` instance — the code returned `cls(db_path)` because `os.path.exists(db_path)` was `True` even though the file is not a valid codegraph database.

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import os, tempfile, sys
sys.path.insert(0, os.getcwd())

from src.languages.codegraph import CodeGraphExtractor

tmp = tempfile.mkdtemp()
os.makedirs(os.path.join(tmp, ".codegraph"))
with open(os.path.join(tmp, ".codegraph", "codegraph.db"), "w") as f:
    f.write("not a valid SQLite database\n")

result = CodeGraphExtractor.from_proj_dir(tmp)
print("result is None:", result is None)
print("result type:", type(result).__name__)
# actual (buggy) output:   result is None: False
#                          result type: CodeGraphExtractor
# expected (correct) output: result is None: True
```

---

## Probe Script

```python
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
```

### Probe Output

```
CONFIRMED — actual: CodeGraphExtractor instance | expected: None
```

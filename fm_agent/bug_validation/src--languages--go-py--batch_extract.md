# Bug Report: batch_extract

**Source file:** `src/languages/go-py/batch_extract.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- Returns a dict whose keys are absolute file paths (strings) of Go source files
    and whose values are lists of (func_name, body) tuples for all function
    definitions extracted from each file
  - func_name is a string containing the canonicalized function identifier; body is
    a string containing the full source text of the function definition
  - Returns an empty dict {} when no codegraph backend is available for Go
  - Only .go source files within proj_dir are processed

---

### Actual Behavior

If CodeGraphExtractor.from_proj_dir(proj_dir) returns None, the function returns an empty dictionary {}. Otherwise, let cg be the returned instance; the function returns cg.get_functions_by_file('go', proj_dir), which is a dict mapping absolute file paths to lists of (func_name, body) tuples with each body ending with newline, tuples ordered by ascending line number, duplicate names disambiguated with numeric suffixes, unreadable source files silently skipped, and an empty dict if 'go' is not a recognized language. Formally: ret = ({} if cg is None else cg.get_functions_by_file('go', proj_dir)).

---

## Code Evidence

Line 4: return cg.get_functions_by_file("go", proj_dir) if cg else {}

---

## Trigger Condition

The code's behavior does not guarantee that only .go files within proj_dir are processed; get_functions_by_file may return file paths outside proj_dir, violating the specification.

---

## How to trigger the bug

When the codegraph database contains file_path entries that use parent-directory traversal (e.g., `../outside/evil.go`), `get_functions_by_file` resolves them via `os.path.join(proj_dir, file_path)` without validating that the resulting absolute path stays within `proj_dir`. The returned dict then includes file paths that escape the project directory.

### Inputs

| Parameter | Value |
|-----------|-------|
| `proj_dir` | A directory containing `.codegraph/codegraph.db` with a `nodes` table that includes an entry where `file_path = "../outside/evil.go"`, `kind = "function"`, `language = "go"` |

### Expected (spec-correct) Output

The returned dict should only contain keys whose absolute paths are within `proj_dir`. The `../outside/evil.go` entry should either be excluded or filtered out.

### Actual (buggy) Output

The returned dict includes a key like `/path/to/project/../outside/evil.go`, which resolves to a location outside `proj_dir`.

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import os
import sys
sys.path.insert(0, os.getcwd())
from src.languages.go import batch_extract

# The codegraph DB at proj_dir/.codegraph/codegraph.db contains a nodes table
# with an entry: file_path="../outside/evil.go", language="go", kind="function"
# and the actual file exists at proj_dir/../outside/evil.go

result = batch_extract(proj_dir)
# actual (buggy) output: dict includes key "proj_dir/../outside/evil.go" (outside proj_dir)
# expected (correct) output: only keys within proj_dir, e.g. "proj_dir/pkg/handler.go"
```

---

## Probe Script

```python
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
```

### Probe Output

```
CONFIRMED — spec requires only files within proj_dir, but returned keys include paths outside proj_dir: ['/tmp/probe_batch_go_p07ik0lo/project/../outside/evil.go']. Inside keys: ['/tmp/probe_batch_go_p07ik0lo/project/pkg/handler.go']
```

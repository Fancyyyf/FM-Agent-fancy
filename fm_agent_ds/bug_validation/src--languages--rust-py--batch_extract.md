# Bug Report: batch_extract

**Source file:** `src/languages/rust.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

If the CodeGraph backend initializes successfully, returns a dict mapping the absolute file path of every Rust source file under proj_dir to an ordered list of (function_name: str, function_body: str) tuples extracted from that file. Each function_name is canonicalized for FQN use. Each function_body is the raw source text of the function definition, including its signature and body. If the CodeGraph backend fails to initialize, returns an empty dict.

---

### Actual Behavior

The function batch_extract either returns normally with a dictionary or raises an exception. On normal return: let cg = CodeGraphExtractor.from_proj_dir(proj_dir). If cg is falsy, the return value is {}. If cg is truthy, the return value is cg.get_functions_by_file("rust", proj_dir), a dictionary mapping each absolute file path of a Rust source file located recursively under proj_dir to a list of (function_name, body) tuples extracted from that file. Under the given pre-condition (proj_dir is a valid directory containing Rust source files), the falsy branch is unreachable, so the result is the complete mapping of all Rust files to their extracted functions. Formal: (  cg := CodeGraphExtractor.from_proj_dir(proj_dir) . (cg = None  not cg)  return = {} )  ( cg  None  cg  return = cg.get_functions_by_file("rust", proj_dir)   f  RustFiles(proj_dir) : abs_path(f)  dom(return)  return[abs_path(f)] = extract_functions(f, "rust") ) . Any exception during from_proj_dir or get_functions_by_file propagates and no dictionary is returned.

---

## Code Evidence

Line 4: return cg.get_functions_by_file("rust", proj_dir) if cg else {}

---

## Trigger Condition

If get_functions_by_file raises an exception, the function propagates the exception instead of returning a dict. The specification states that the function returns a dict (empty on initialization failure, full mapping on success) and does not allow exceptions to propagate.

---

## How to trigger the bug

The function only handles the case where the CodeGraph backend fails to initialize (`cg` is falsy → returns `{}`). When `cg` is truthy (the `.codegraph/codegraph.db` file exists on disk), `from_proj_dir` returns a `CodeGraphExtractor` instance, and `get_functions_by_file` is called. However, `from_proj_dir` only checks file existence via `os.path.exists()`, not file validity. If the DB file exists but is not a valid SQLite database (e.g. corrupted or replaced with a text file), `get_functions_by_file` raises a `sqlite3.DatabaseError`, which propagates uncaught through `batch_extract`. Per the spec, the function should return a dict — an empty dict is the natural fallback — but instead the exception leaks to the caller.

### Inputs

| Parameter | Value |
|-----------|-------|
| `proj_dir` | A temporary directory containing `.codegraph/codegraph.db` that exists but is not a valid SQLite database (e.g. contains the text `"this is not a valid sqlite database file"`) |

### Expected (spec-correct) Output

`{}` (empty dict)

### Actual (buggy) Output

`sqlite3.DatabaseError: file is not a database` (exception propagates)

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import sys
import os
import tempfile
sys.path.insert(0, os.getcwd())
from src.languages.rust import batch_extract

with tempfile.TemporaryDirectory() as tmpdir:
    os.makedirs(os.path.join(tmpdir, ".codegraph"))
    with open(os.path.join(tmpdir, ".codegraph", "codegraph.db"), "w") as f:
        f.write("not a database")
    result = batch_extract(tmpdir)
    print(result)
# actual (buggy) output: sqlite3.DatabaseError: file is not a database
# expected (correct) output: {}
```

---

## Probe Script

```python
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
```

### Probe Output

```
CONFIRMED — batch_extract raised exception instead of returning a dict: DatabaseError: file is not a database
```

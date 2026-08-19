# Bug Report: function_spans

**Source file:** `fm_agent/extracted_functions/src/languages/java-py/function_spans.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

When the project's code analysis backend is available, returns a list of (func_name: str, start_idx: int, end_idx: int) tuples. Each tuple identifies one function defined in the file  func_name is the function's identifier, start_idx and end_idx are 0-indexed inclusive line numbers bounding the function's source range within the file. The returned list preserves the order in which functions appear in the source file. Returns None when the backend is unavailable for the project, indicating that the caller must determine function boundaries through a language-specific regex-based fallback.

---

### Actual Behavior

The function returns `None` if `CodeGraphExtractor.from_proj_dir(proj_dir)` evaluates to a falsy value (indicating the code index cannot be loaded) or if the method `get_function_spans('java', filepath)` on the resulting extractor returns `None` (meaning the file is not present in the index). Otherwise, the return value is a list of `(func_name: str, start_idx: int, end_idx: int)` tuples, one per function definition in the Java source file at `filepath`, where `start_idx` and `end_idx` are 0-indexed inclusive line numbers. Formally: let `cg = CodeGraphExtractor.from_proj_dir(proj_dir)`. If `cg` is falsy, then `result = None`. If `cg` is truthy, let `spans = cg.get_function_spans('java', filepath)`; if `spans` is `None` or falsy, then `result = None`; otherwise `result = spans` and `result` is a list of triples satisfying ` t  result : (isinstance(t, tuple)  len(t) == 3  isinstance(t[0], str)  isinstance(t[1], int)  isinstance(t[2], int)  0  t[1]  t[2])`.

---

## Code Evidence

Line 8: return cg.get_function_spans("java", filepath) if cg else None

---

## Trigger Condition

When the backend is available (cg is truthy) but the file is not present in the index, get_function_spans returns None, causing the function to return None. The specification requires that whenever the backend is available, the function must return a list of function span tuples; it does not permit returning None for an unindexed file.

---

## How to trigger the bug

When the codegraph backend is available (`.codegraph/codegraph.db` exists in the project directory) but the target Java file has no entries in the `nodes` table, `function_spans` returns `None` instead of a list. The spec requires that `None` be returned ONLY when the backend itself is unavailable, so the caller can distinguish "backend not available, use regex fallback" from "backend available but file not indexed." Returning `None` in both cases forces the caller to fall back to regex even when the backend is healthy, defeating the purpose of having a backend.

### Inputs

| Parameter | Value |
|-----------|-------|
| `proj_dir` | `/tmp/probe_function_spans_XXXXXX` (temp dir containing `.codegraph/codegraph.db` with empty `nodes` table) |
| `filepath` | `/tmp/probe_function_spans_XXXXXX/Nonexistent.java` (file not indexed in codegraph) |

### Expected (spec-correct) Output

`[]` (empty list — backend is available, no functions found for this file)

### Actual (buggy) Output

`None` (the function returns `None` even though the backend is available)

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import os
import sqlite3
import tempfile
from src.languages.java import function_spans

tmpdir = tempfile.mkdtemp(prefix="probe_function_spans_")
codegraph_dir = os.path.join(tmpdir, ".codegraph")
os.makedirs(codegraph_dir)
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

result = function_spans(tmpdir, os.path.join(tmpdir, "Nonexistent.java"))
print(result)  # actual (buggy) output: None
# expected (correct) output: []
```

---

## Probe Script

```python
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
```

### Probe Output

```
CONFIRMED — function_spans returned None even though CodeGraphExtractor was loaded (backend available). The spec requires a list when the backend is available; None should only mean 'backend unavailable, use fallback'.
```

# Bug Report: call_edges

**Source file:** `/home/fancy/Projects_Vault/FM-Agent/fm_agent/extracted_functions/src/languages/go-py/call_edges.py`
**Verdict:** MISMATCH
**Confirmation status:** not_confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

When the CodeGraph backend can index the project's Go code, returns a dict whose keys are canonicalized caller FQNs (using :: as the namespace separator) and whose values are sets of canonicalized callee FQNs, representing the call-graph edges for Go source files in the project. When the CodeGraph backend is unavailable, returns None.

---

### Actual Behavior

If the CodeGraph index for the project directory can be created (i.e., CodeGraphExtractor.from_proj_dir(proj_dir) returns a non-None instance), the function returns a dictionary that maps each caller's fully qualified name (as a tuple of caller_stem and caller_module, or a single string depending on implementation) to a set of callee stems for the Go language. If the index cannot be created (from_proj_dir returns None), the function returns None. No external state is modified, and the function does not raise exceptions under normal operation. Formal logic: Let R = call_edges(proj_dir). Then (R = None)  (R  None   cg  None, cg = CodeGraphExtractor.from_proj_dir(proj_dir)  R = cg.get_call_edges('go')  R is a dict mapping caller FQNs to sets of callee FQNs for Go).

---

## Code Evidence

Line 2: """Return {(caller_stem, caller_module): {callee_stems}} for Go."""
Line 4: return cg.get_call_edges("go") if cg else None

---

## Trigger Condition

The code returns keys as tuples (caller_stem, caller_module) instead of canonicalized strings using '::' as the namespace separator, violating the specification's requirement for the dict key format.

---

## How to trigger the bug

The probe creates a minimal codegraph SQLite database with a Go caller-callee pair ("main.main" calling "main.helper" in "main.go"), then invokes `call_edges()` on that directory. The actual return value was inspected: `get_call_edges("go")` builds FQNs via the `_fqn_for(file_path, deduped)` helper, which always produces `::`-separated strings (e.g., `"main-go::main::main"`). The docstring on line 2 is inaccurate (it describes the key as a tuple), but the *actual runtime behavior* returns string keys that match the specification.

### Inputs

| Parameter | Value |
|-----------|-------|
| `proj_dir` | Temporary directory containing `.codegraph/codegraph.db` with one Go caller and one Go callee |

### Expected (spec-correct) Output

`{"main-go::main::main": {"main-go::main::helper"}}` — dict with `::`-separated FQN string keys and set-of-strings values.

### Actual (buggy) Output

`{"main-go::main::main": {"main-go::main::helper"}}` — identical to the expected output. Keys are strings, not tuples.

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import os, sqlite3, tempfile, sys

# Create a minimal codegraph DB with Go data
tmpdir = tempfile.mkdtemp()
os.makedirs(os.path.join(tmpdir, ".codegraph"))
db_path = os.path.join(tmpdir, ".codegraph", "codegraph.db")
conn = sqlite3.connect(db_path)
conn.execute("CREATE TABLE nodes (id INTEGER PRIMARY KEY, name TEXT, qualified_name TEXT, file_path TEXT, start_line INTEGER, end_line INTEGER, kind TEXT, language TEXT)")
conn.execute("CREATE TABLE edges (source INTEGER, target INTEGER, kind TEXT)")
conn.execute("INSERT INTO nodes VALUES (1, 'main', 'main.main', 'main.go', 1, 10, 'function', 'go')")
conn.execute("INSERT INTO nodes VALUES (2, 'helper', 'main.helper', 'main.go', 12, 15, 'function', 'go')")
conn.execute("INSERT INTO edges VALUES (1, 2, 'calls')")
conn.commit(); conn.close()

from src.languages.go import call_edges
result = call_edges(tmpdir)
print(list(result.keys()))  # ['main-go::main::main'] — strings, not tuples
// actual (buggy) output: N/A — output matches spec
// expected (correct) output: ["main-go::main::main"] (string keys)
```

---

## Probe Script

```python
import os
import sqlite3
import sys
import tempfile
import shutil


def main():
    """Probe: verify call_edges key format is strings, not tuples.

    The spec requires keys as canonicalized ::-separated FQN strings.
    The trigger_condition claims keys are returned as tuples.
    """
    repo_root = os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    )
    sys.path.insert(0, repo_root)

    try:
        from src.languages.go import call_edges
    except Exception as e:
        print(f"ERROR: cannot import call_edges — {e}")
        sys.exit(1)

    # Create a temp directory with a minimal codegraph SQLite DB.
    tmpdir = tempfile.mkdtemp(prefix="probe_go_call_edges_")
    cg_dir = os.path.join(tmpdir, ".codegraph")
    os.makedirs(cg_dir, exist_ok=True)
    db_path = os.path.join(cg_dir, "codegraph.db")

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # Minimal codegraph schema.
    cur.execute(
        """
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
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS edges (
            source INTEGER,
            target INTEGER,
            kind TEXT
        )
        """
    )

    # Insert a caller (Go function) and a callee.
    cur.execute(
        "INSERT INTO nodes VALUES (1, 'main', 'main.main', 'main.go', 1, 10, 'function', 'go')"
    )
    cur.execute(
        "INSERT INTO nodes VALUES (2, 'helper', 'main.helper', 'main.go', 12, 15, 'function', 'go')"
    )
    cur.execute("INSERT INTO edges VALUES (1, 2, 'calls')")
    conn.commit()
    conn.close()

    # Call the function under test.
    try:
        result = call_edges(tmpdir)
    except Exception as e:
        print(f"ERROR: call_edges raised — {type(e).__name__}: {e}")
        shutil.rmtree(tmpdir, ignore_errors=True)
        sys.exit(1)

    if result is None:
        print("ERROR: call_edges returned None (codegraph DB was not detected)")
        shutil.rmtree(tmpdir, ignore_errors=True)
        sys.exit(1)

    if not isinstance(result, dict):
        print(
            f"NOT CONFIRMED — unexpected return type: {type(result).__name__}, "
            "expected a dict"
        )
        shutil.rmtree(tmpdir, ignore_errors=True)
        return

    # Check key types.
    keys_are_strings = all(isinstance(k, str) for k in result)
    keys_are_tuples = any(isinstance(k, tuple) for k in result)

    spec_claim = (
        "keys are canonicalized caller FQNs using :: as namespace separator"
    )

    if keys_are_strings:
        # Verify the strings actually contain :: separators (FQN format)
        fqn_like = any("::" in k for k in result)
        print(
            f"NOT CONFIRMED — keys are strings ({list(result.keys())}), "
            f"::-separated FQN format present: {fqn_like}. "
            f"This matches the spec ({spec_claim}), "
            f"not the claimed bug (tuple keys)."
        )
    elif keys_are_tuples:
        print(
            f"CONFIRMED — keys are tuples: {list(result.keys())!r}. "
            f"Spec requires {spec_claim}."
        )
    else:
        print(
            f"NOT CONFIRMED — unexpected key type(s): "
            f"{[type(k).__name__ for k in result.keys()]}"
        )

    shutil.rmtree(tmpdir, ignore_errors=True)


if __name__ == "__main__":
    main()
```

### Probe Output

```
NOT CONFIRMED — keys are strings (['main-go::main::main']), ::-separated FQN format present: True. This matches the spec (keys are canonicalized caller FQNs using :: as namespace separator), not the claimed bug (tuple keys).
```

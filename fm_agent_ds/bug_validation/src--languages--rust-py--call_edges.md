# Bug Report: call_edges

**Source file:** `/home/fancy/Projects_Vault/FM-Agent/fm_agent/extracted_functions/src/languages/rust-py/call_edges.py`
**Verdict:** MISMATCH
**Confirmation status:** not_confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

If the CodeGraph backend initializes successfully, returns a dict mapping each Rust caller identifier to a set of callee identifiers for all Rust source files under proj_dir. Both caller and callee identifiers use the canonicalized FQN format. If the CodeGraph backend fails to initialize, returns None.

---

### Actual Behavior

After the function finishes execution normally, the return value R is determined as follows: if the call CodeGraphExtractor.from_proj_dir(proj_dir) returns an object O that is truthy, then R = O.get_call_edges("rust") and R is a dictionary mapping tuples of the form (caller_stem, caller_module) to sets of callee_stems. If O is falsy, R = None. The function does not modify proj_dir or any global state. If an exception is raised during the execution of CodeGraphExtractor.from_proj_dir(proj_dir), the exception propagates, and no normal return occurs. Formally: let cg = CodeGraphExtractor.from_proj_dir(proj_dir); then (normal_return  ((cg  None  cg  False  ...)  result = cg.get_call_edges("rust")  result is dict with said structure)  (cg  result = None))  (exception  no return).

---

## Code Evidence

Line 4: return cg.get_call_edges("rust") if cg else None

---

## Trigger Condition

The specification explicitly requires that both caller and callee identifiers use the canonicalized FQN format, but the code (as documented and implemented) returns caller identifiers as (caller_stem, caller_module) tuples and callee identifiers as bare stems, violating the required output format.

---

## How to trigger the bug

The probe created a mock codegraph SQLite database with two Rust functions (`main` in `src/main.rs`, `helper` in `src/utils.rs`) and a call edge from `main` to `helper`. Calling `CodeGraphExtractor.get_call_edges("rust")` with this database returns call edge data.

The actual runtime output uses FQN-format string keys and FQN-format string values, matching the specification. The bug claim that the code returns `(caller_stem, caller_module)` tuples and bare-stem callees is not supported by the runtime behavior.

This is a false positive: the logic verification compared the spec ("canonicalized FQN format") against the extracted function's **docstring** (`Return {(caller_stem, caller_module): {callee_stems}}`), which was an inaccurate summarization by the extraction step. The actual `get_call_edges` implementation (in `src/languages/codegraph.py`) builds FQNs via `_fqn_for()` and returns `{caller_fqn_str: {callee_fqn_str, ...}}`, fully satisfying the spec.

### Inputs

| Parameter | Value |
|-----------|-------|
| `proj_dir` | Temporary directory containing `.codegraph/codegraph.db` with mock Rust nodes and edges |

### Expected (spec-correct) Output

`{caller_fqn_str: {callee_fqn_str, ...}}` — strings in canonicalized FQN format (`dir::file-ext::name`)

### Actual (buggy) Output

`{'src::main-rs::main': {'src::utils-rs::helper'}}` — FQN strings, matching the spec

### How to Reproduce

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import os
import sqlite3
import tempfile
from src.languages.codegraph import CodeGraphExtractor

tmpdir = tempfile.mkdtemp()
codegraph_dir = os.path.join(tmpdir, ".codegraph")
os.makedirs(codegraph_dir, exist_ok=True)
db_path = os.path.join(codegraph_dir, "codegraph.db")

conn = sqlite3.connect(db_path)
cur = conn.cursor()
cur.execute("CREATE TABLE nodes (id INTEGER, name TEXT, qualified_name TEXT, file_path TEXT, kind TEXT, language TEXT, start_line INTEGER)")
cur.execute("CREATE TABLE edges (source INTEGER, target INTEGER, kind TEXT)")
cur.execute("INSERT INTO nodes VALUES (1, 'main', 'main', 'src/main.rs', 'function', 'rust', 1)")
cur.execute("INSERT INTO nodes VALUES (2, 'helper', 'helper', 'src/utils.rs', 'function', 'rust', 5)")
cur.execute("INSERT INTO edges VALUES (1, 2, 'calls')")
conn.commit()
conn.close()

extractor = CodeGraphExtractor(db_path)
result = extractor.get_call_edges("rust")
# actual (buggy) output: {'src::main-rs::main': {'src::utils-rs::helper'}}
# expected (correct) output: {'src::main-rs::main': {'src::utils-rs::helper'}}
# Both caller and callee are FQN strings — matches spec, contradicts bug claim
```

---

## Probe Script

```python
"""Probe for bug src--languages--rust-py--call_edges.

Claims: get_call_edges("rust") returns (caller_stem, caller_module) tuple keys
and bare-stem callees, violating the spec that requires FQN format.
"""
import os
import re
import sqlite3
import sys
import tempfile

try:
    from src.languages.codegraph import CodeGraphExtractor

    # Create a temporary directory with a mock .codegraph/codegraph.db
    tmpdir = tempfile.mkdtemp()
    codegraph_dir = os.path.join(tmpdir, ".codegraph")
    os.makedirs(codegraph_dir, exist_ok=True)
    db_path = os.path.join(codegraph_dir, "codegraph.db")

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute(
        "CREATE TABLE nodes ("
        "  id INTEGER, name TEXT, qualified_name TEXT,"
        "  file_path TEXT, kind TEXT, language TEXT, start_line INTEGER"
        ")"
    )
    cur.execute(
        "CREATE TABLE edges (source INTEGER, target INTEGER, kind TEXT)"
    )

    # Insert two Rust functions
    cur.execute(
        "INSERT INTO nodes VALUES "
        "(1, 'main', 'main', 'src/main.rs', 'function', 'rust', 1)"
    )
    cur.execute(
        "INSERT INTO nodes VALUES "
        "(2, 'helper', 'helper', 'src/utils.rs', 'function', 'rust', 5)"
    )
    # Call edge: main -> helper
    cur.execute("INSERT INTO edges VALUES (1, 2, 'calls')")
    conn.commit()
    conn.close()

    extractor = CodeGraphExtractor(db_path)
    result = extractor.get_call_edges("rust")

    # --- Verify the output format against the spec ---

    # Spec: "caller identifiers use the canonicalized FQN format" → must be str
    caller_types_ok = all(isinstance(k, str) for k in result)
    # Bug claim: returns (caller_stem, caller_module) tuples → would fail
    caller_is_tuple = any(isinstance(k, tuple) for k in result)

    # Spec: "callee identifiers use the canonicalized FQN format" → each must be str
    callee_types_ok = all(
        isinstance(v, set)
        and all(isinstance(item, str) for item in v)
        for v in result.values()
    )
    # Bug claim: callees are bare stems → check FQN pattern (contains ::)
    fqn_pattern = re.compile(r"::")
    callee_has_fqn = (
        all(
            fqn_pattern.search(item)
            for v in result.values()
            for item in v
        )
        if result
        else True  # vacuously true for empty result
    )

    # Print diagnostics
    print(f"Result keys: {list(result.keys())}")
    for k, v in result.items():
        print(f"  caller={k!r} (type={type(k).__name__}) -> callees={v!r}")
    print()
    print(f"Caller keys are strings (FQN):    {caller_types_ok}")
    print(f"Caller keys are tuples (claimed): {caller_is_tuple}")
    print(f"Callees are strings (FQN):        {callee_types_ok}")
    print(f"Callees contain '::' (FQN):       {callee_has_fqn}")

    # Verdict: spec says FQN format. If callers are strings (not tuples) AND
    # callees are strings (not bare stems), the code matches the spec.
    if caller_types_ok and not caller_is_tuple and callee_types_ok:
        print()
        print(
            "NOT CONFIRMED — caller identifiers are FQN strings (not tuples), "
            "callee identifiers are FQN strings (not bare stems). "
            "Actual behaviour matches the specification."
        )
    else:
        print()
        print(
            "CONFIRMED — output format does not match the FQN spec claim"
        )

except Exception as e:
    import traceback

    print(f"ERROR: {e}")
    traceback.print_exc()
    sys.exit(1)
finally:
    # Cleanup temporary directory
    import shutil

    if "tmpdir" in dir() and os.path.isdir(tmpdir):
        shutil.rmtree(tmpdir, ignore_errors=True)
```

### Probe Output

```
Result keys: ['src::main-rs::main']
  caller='src::main-rs::main' (type=str) -> callees={'src::utils-rs::helper'}

Caller keys are strings (FQN):    True
Caller keys are tuples (claimed): False
Callees are strings (FQN):        True
Callees contain '::' (FQN):       True

NOT CONFIRMED — caller identifiers are FQN strings (not tuples), callee identifiers are FQN strings (not bare stems). Actual behaviour matches the specification.
```

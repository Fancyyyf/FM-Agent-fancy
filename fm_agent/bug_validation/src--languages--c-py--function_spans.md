# Bug Report: function_spans

**Source file:** `src/languages/c.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- Returns None when a codegraph instance cannot be initialized from proj_dir
- Otherwise returns a list of (function_name, start_idx, end_idx) tuples for every
    function defined in the C source file at filepath, where start_idx and end_idx
    are 0-indexed inclusive line numbers

---

### Actual Behavior

The code block either raises an exception during CodeGraphExtractor construction or method call, or it terminates normally and returns a value r. In the normal case, r is either None (indicating the codegraph is unavailable or does not index the given file) or a list of tuples, each of the form (name: str, start: int, end: int) with start <= end and both indices nonnegative, representing 0indexed inclusive line spans of C function definitions extracted from filepath. Formally: (normal_termination)  ( (r = None)  ( (r = [(name_1, start_1, end_1), , (name_k, start_k, end_k)])  ( i  {1,,k} : type(name_i)=str  type(start_i)=int  type(end_i)=int  0  start_i  end_i) ) ).

---

## Code Evidence

Line 8: return cg.get_function_spans("c", filepath) if cg else None

---

## Trigger Condition

The specification mandates that if a codegraph instance can be initialized from proj_dir, the function must return a list of function spans. The code can return None even when cg is truthy, because it passes through the result of get_function_spans, which may be None if the file is not indexed. This violates the 'Otherwise returns a list' requirement.

---

## How to trigger the bug

The function `function_spans(proj_dir, filepath)` at `src/languages/c.py` creates a `CodeGraphExtractor` via `from_proj_dir(proj_dir)`. The spec says: return `None` ONLY when codegraph cannot be initialized; otherwise return a **list**. But when `cg` is truthy (codegraph initialized) and the target file is not in the index, `cg.get_function_spans("c", filepath)` returns `None`, and the function passes that `None` straight through — violating the spec mandate that a list must be returned whenever `cg` is truthy.

### Inputs

| Parameter | Value |
|-----------|-------|
| `proj_dir` | `/tmp/fm_agent_wt_FM-Agent_dlsr6ukl/snapshot` (contains `.codegraph/codegraph.db`) |
| `filepath` | `/tmp/fm_agent_wt_FM-Agent_dlsr6ukl/snapshot/_probe_unindexed.c` (not in codegraph index) |

### Expected (spec-correct) Output

`[]` (empty list — the spec mandates a list whenever codegraph is initialized)

### Actual (buggy) Output

`None` (passed through from `cg.get_function_spans()`)

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
from src.languages.c import function_spans

# proj_dir with a valid .codegraph/codegraph.db
# filepath to a .c file NOT indexed by codegraph
result = function_spans("/path/to/proj_dir", "/path/to/unindexed_file.c")
# actual (buggy) output: None
# expected (correct) output: []  (a list)
```

---

## Probe Script

```python
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
```

### Probe Output

```
CONFIRMED — actual: None | expected: []
```

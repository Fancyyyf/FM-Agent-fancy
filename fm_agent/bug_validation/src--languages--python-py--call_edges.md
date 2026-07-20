# Bug Report: call_edges

**Source file:** `src/languages/python.py`
**Verdict:** MISMATCH
**Confirmation status:** not_confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- Returns a dict when the CodeGraph backend can index the project directory; returns None when the backend is unavailable or the project cannot be indexed.
  - When a dict is returned, each key identifies a caller function (as a tuple of stem and module identifiers) and each value is a set of callee function identifiers (stems) called by that caller.
  - The returned call edges cover Python source files (.py) under the project directory.
  - A callee appears in the returned set only when the CodeGraph backend resolves a call site within the caller's body to that callee.

---

### Actual Behavior

If the CodeGraphExtractor backend is available and the project can be indexed, the function returns a dictionary mapping each (caller_stem, caller_module) tuple to a set of callee_stem strings for Python; otherwise, it returns None. Formally: let cg = CodeGraphExtractor.from_proj_dir(proj_dir). If cg is falsy, the result is None. If cg is truthy, let edges = cg.get_call_edges('python'). If edges is None, the result is None; else the result is a Dict[Tuple[str, str], Set[str]] containing the call graph edges.

---

## Code Evidence

Line 4: return cg.get_call_edges("python") if cg else None

---

## Trigger Condition

The specification mandates that the function returns a dict whenever the backend can index the project directory. The code returns None if cg is truthy but cg.get_call_edges('python') returns None, which contradicts the spec. A concrete case is a valid project directory that the backend can index but for which no Python call edges can be resolved (e.g., no .py files), leading to a None return while a dict is expected.

---

## How to trigger the bug

The `call_edges` function (line 10-13 of `src/languages/python.py`) delegates to `CodeGraphExtractor.get_call_edges("python")`. The spec requires returning a dict whenever the backend can index the project directory. The code could theoretically return None if `get_call_edges` were to return None — however, `CodeGraphExtractor.get_call_edges()` always returns a dict for the "python" language key (either `{}` or a populated dict). The None-return code path is unreachable with the current backend implementation.

### Inputs

| Parameter | Value |
|-----------|-------|
| `proj_dir` | Repo root (contains `.codegraph/codegraph.db` — backend available) |

### Expected (spec-correct) Output

A dict (mapping caller tuples to callee sets) — because the backend can index the project directory.

### Actual (buggy) Output

A dict with 219 caller entries — the function correctly returns a dict, matching the spec.

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
from src.languages.python import call_edges
from src.languages.codegraph import CodeGraphExtractor

proj_dir = "."   # has .codegraph/codegraph.db
cg = CodeGraphExtractor.from_proj_dir(proj_dir)
# backend IS available: cg is truthy
result = call_edges(proj_dir)
# actual (buggy) output: dict with 219 callers
# expected (correct) output: dict
# Note: the buggy path (get_call_edges returns None causing call_edges to return None)
# is unreachable — CodeGraphExtractor.get_call_edges() always returns a dict for "python".
```

---

## Probe Script

```python
import sys
import os

# Ensure the repo root is on sys.path so 'import src' resolves
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

try:
    from src.languages.python import call_edges
    from src.languages.codegraph import CodeGraphExtractor

    # ── Bug Description ────────────────────────────────────────────────
    # Spec claim: "Returns a dict when the CodeGraph backend can index
    #   the project directory; returns None when the backend is
    #   unavailable or the project cannot be indexed."
    # Code:       return cg.get_call_edges("python") if cg else None
    # Gap:        When cg is truthy (backend available) but
    #             cg.get_call_edges("python") returns None, the function
    #             returns None — violating the spec which demands a dict.
    # ────────────────────────────────────────────────────────────────────

    proj_dir = REPO_ROOT   # has .codegraph/codegraph.db — backend available

    # Verify the backend IS available (cg should be truthy)
    cg = CodeGraphExtractor.from_proj_dir(proj_dir)
    backend_available = cg is not None

    # Call the function under test via its public entry point
    result = call_edges(proj_dir)

    # ── Verification ───────────────────────────────────────────────────
    # Spec says: when backend can index → MUST return a dict
    # Code says:  return cg.get_call_edges("python") if cg else None
    # If result is a dict → function behaves per spec (bug NOT reproduced)
    # If result is None → function violates spec (bug CONFIRMED)

    if not backend_available:
        # Backend not available — spec expects None, code returns None → correct
        if result is None:
            print("NOT CONFIRMED — backend unavailable, returned None as expected")
        else:
            print(f"UNEXPECTED: backend unavailable but result is {type(result).__name__}")
            sys.exit(1)
    else:
        # Backend IS available — spec demands a dict
        if isinstance(result, dict):
            num_edges = len(result)
            print("NOT CONFIRMED")
            print(f"  reason: backend available (cg is truthy), call_edges returned a dict ({num_edges} callers)")
            print(f"  spec: Returns a dict when backend can index — satisfied")
            print(f"  code: get_call_edges('python') returned a dict, not None")
            print("  note: CodeGraphExtractor.get_call_edges() always returns dict for 'python';")
            print("        the None-return code path in call_edges is unreachable with the current backend")
        else:
            bug_desc = f"backend available but call_edges returned {type(result).__name__} instead of dict"
            actual_desc = repr(result)
            expected_desc = "dict"
            print("CONFIRMED")
            print(f"  actual:   {actual_desc!r}")
            print(f"  expected: {expected_desc!r}")
            print(f"  description: {bug_desc}")

except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)
```

### Probe Output

```
NOT CONFIRMED
  reason: backend available (cg is truthy), call_edges returned a dict (219 callers)
  spec: Returns a dict when backend can index — satisfied
  code: get_call_edges('python') returned a dict, not None
  note: CodeGraphExtractor.get_call_edges() always returns dict for 'python';
        the None-return code path in call_edges is unreachable with the current backend
```

# Bug Report: _normalize_backend

**Source file:** `/tmp/fm_agent_wt_FM-Agent_dlsr6ukl/snapshot/fm_agent/extracted_functions/src/cli_backend-py/_normalize_backend.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- When value is None, or when its normalized form is the empty string,
    or when the normalized form is one of the recognized disable-sentinel
    strings ("0", "false", "no", "off"): returns "opencode", the canonical
    name of the default backend
  - When the normalized form equals "auto": returns "auto" unchanged,
    deferring resolution of the auto-sentinel to the caller
  - When the normalized form matches a recognized backend alias:
    returns the canonical backend name that the alias maps to
    (aliases map to the set {"opencode", "codex-cli", "claude-cli"})
  - When the normalized form matches none of the above categories:
    returns the normalized form itself unchanged as a pass-through
  - The returned string is always non-empty, case-normalized to lowercase,
    and drawn from the set {"opencode", "codex-cli", "claude-cli", "auto"}
    unioned with the domain of unrecognized pass-through strings
  - The same input value always produces the same output (pure function)
  - Returns a str in all cases  no exceptions are raised for any input

---

### Actual Behavior

The function returns a string. Let b = (value or "").strip().lower(). If b is empty or b  {"0", "false", "no", "off"}, return "opencode". If b == "auto", return "auto". Otherwise, return _BACKEND_ALIASES.get(b, b). Formally: result = "opencode" if (b == "" or b in {"0","false","no","off"}) else ("auto" if b == "auto" else (_BACKEND_ALIASES[b] if b in _BACKEND_ALIASES else b)). The function never raises an exception under the given pre-condition.

---

## Code Evidence

Line 2: backend = (value or "").strip().lower()

---

## Trigger Condition

The specification requires that the function returns a str for any input and never raises an exception. For value=1 (an integer), (1 or '') evaluates to 1, which has no .strip() method, so the code raises AttributeError, violating the specification.

---

## How to trigger the bug

The bug can be triggered by passing an integer value to `_normalize_backend`, which is called indirectly through the public function `build_agent_command` (also via `resolve_model_backend`, but that always passes string or None from environment). When `value` is a non-string, non-None object (e.g. `int`), the expression `(value or "")` evaluates to the object itself (since non-None truthy objects are returned by the `or` operator), and the object may not have a `.strip()` method, causing an `AttributeError`.

### Inputs

| Parameter | Value |
|-----------|-------|
| model | `"test-model"` |
| prompt | `"test prompt"` |
| cwd | `"/tmp"` |
| backend | `1` (integer) |

### Expected (spec-correct) Output

No exception — the function should handle the integer input gracefully. Per the spec, `str(1)` → `"1"`, which after normalization is `"1"` (an unrecognized pass-through), so it should return `"1"`.

### Actual (buggy) Output

`AttributeError: 'int' object has no attribute 'strip'`

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
from src.cli_backend import build_agent_command
build_agent_command(model="test-model", prompt="test prompt", cwd="/tmp", backend=1)
# actual (buggy) output: AttributeError: 'int' object has no attribute 'strip'
# expected (correct) output: no exception raised
```

---

## Probe Script

```python
import sys
sys.path.insert(0, '/tmp/fm_agent_wt_FM-Agent_dlsr6ukl/snapshot')

try:
    from src.cli_backend import build_agent_command

    # Spec claim: returns a str in all cases, never raises for any input
    # Bug: _normalize_backend(int) does (int or "").strip().lower() — int has no .strip()
    passed = False
    try:
        build_agent_command(model="test-model", prompt="test prompt", cwd="/tmp", backend=1)
        # If we reach here, no exception raised — bug NOT reproduced
    except AttributeError as e:
        passed = True
        print(f"CONFIRMED — AttributeError raised: {e}")
    except Exception as e:
        print(f"ERROR — unexpected exception type: {type(e).__name__}: {e}")
        sys.exit(1)

    if not passed:
        print("NOT CONFIRMED — no AttributeError raised for integer backend=1")

except Exception as e:
    print(f"ERROR during import: {e}")
    sys.exit(1)
```

### Probe Output

```
CONFIRMED — AttributeError raised: 'int' object has no attribute 'strip'
```

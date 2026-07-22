# Bug Report: _timeout_seconds

**Source file:** `/tmp/fm_agent_wt_FM-Agent_xyeqtgt6/snapshot/fm_agent/extracted_functions/src/languages/erlang-py/_timeout_seconds.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- Returns an integer ≥ 1 representing the maximum number of seconds to wait for
    a single LSP operation
  - When the environment variable `ELP_TIMEOUT_SECONDS` is set to a string
    representing a decimal integer n, the returned value is n when n ≥ 1, and 1
    when n < 1
  - When `ELP_TIMEOUT_SECONDS` is not set, or is set to a string that is not a
    valid decimal integer representation, the returned value is the built-in
    default constant `_DEFAULT_TIMEOUT_SECONDS`

---

### Actual Behavior

The function returns an integer, which is always at least 1. Formally: isinstance(result, int) ∧ result ≥ 1.

---

## Code Evidence

Line 1: def _timeout_seconds() -> int:
Line 4:     return max(1, settings.erlang.timeout_s)

---

## Trigger Condition

The specification (B) mandates that when ELP_TIMEOUT_SECONDS is missing or invalid, the function must return _DEFAULT_TIMEOUT_SECONDS. The code never reads the environment variable and never references _DEFAULT_TIMEOUT_SECONDS; it only returns max(1, settings.erlang.timeout_s). Even if the config loader normally sets the default, the function's own logic does not enforce the specified fallback, so there exist states (e.g., settings.erlang.timeout_s ≠ _DEFAULT_TIMEOUT_SECONDS) where the output violates B.

---

## How to trigger the bug

The function `_timeout_seconds()` delegates the entire default-value and env-var resolution to the external config object (`settings.erlang.timeout_s`) rather than reading `ELP_TIMEOUT_SECONDS` itself and falling back to the built-in constant `_DEFAULT_TIMEOUT_SECONDS`. The constant `_DEFAULT_TIMEOUT_SECONDS` does not exist anywhere in the codebase. When `settings.erlang.timeout_s` is mutated to a value that diverges from the intended default (180), the function silently returns the mutated value even though the spec requires the constant `_DEFAULT_TIMEOUT_SECONDS` when `ELP_TIMEOUT_SECONDS` is not set.

### Inputs

| Parameter | Value |
|-----------|-------|
| `ELP_TIMEOUT_SECONDS` env var | not set |
| `settings.erlang.timeout_s` | 30 (diverged from default 180) |
| No function arguments | — |

### Expected (spec-correct) Output

`180` (the built-in default constant `_DEFAULT_TIMEOUT_SECONDS`)

### Actual (buggy) Output

`30` (returns `max(1, settings.erlang.timeout_s)` = `max(1, 30)` = `30`)

### How to Reproduce

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from config import settings
from src.languages.erlang import _timeout_seconds

os.environ.pop('ELP_TIMEOUT_SECONDS', None)
settings.erlang.timeout_s = 30          # diverge from the default

actual   = _timeout_seconds()
expected = 180                           # _DEFAULT_TIMEOUT_SECONDS

# actual (buggy) output: 30
# expected (correct) output: 180
# mismatch: 30 != 180
```

---

## Probe Script

```python
import os
import sys

# Run from repo root; ensure the repo root is on sys.path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

try:
    from config import settings
    from src.languages.erlang import _timeout_seconds

    _DEFAULT_TIMEOUT_SECONDS = 180

    # Ensure ELP_TIMEOUT_SECONDS is NOT in the environment
    os.environ.pop("ELP_TIMEOUT_SECONDS", None)

    # Modify settings to diverge from the default constant.
    # The spec says: when ELP_TIMEOUT_SECONDS is not set → return _DEFAULT_TIMEOUT_SECONDS.
    # The code reads settings.erlang.timeout_s, so changing it to a non-default
    # value should NOT affect the output — but it does.
    settings.erlang.timeout_s = 30

    actual = _timeout_seconds()
    expected = _DEFAULT_TIMEOUT_SECONDS  # spec-required fallback

    passed = actual != expected

except Exception as e:
    print(f"ERROR: {type(e).__name__}: {e}")
    sys.exit(1)

if passed:
    print(f"CONFIRMED — actual: {actual!r} | expected: {expected!r}")
else:
    print(f"NOT CONFIRMED — actual matched expected: {actual!r}")
```

### Probe Output

```
CONFIRMED — actual: 30 | expected: 180
```

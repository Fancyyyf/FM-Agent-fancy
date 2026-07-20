# Bug Report: resolve_model_backend

**Source file:** `src/cli_backend.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- Returns a canonical backend identifier string: one of "opencode",
    "codex-cli", or "claude-cli"
  - When FM_AGENT_MODEL_BACKEND is set and its alias-normalized value
    is not the sentinel "auto", returns the normalized value directly
  - When FM_AGENT_MODEL_BACKEND is absent from the environment or its
    normalized value is "auto", the backend is determined by inspecting
    environment markers in a fixed priority order:
      1. FM_AGENT_HOST or FM_AGENT_CLIENT (whichever is set) is checked
         case-insensitively for "claude" or "codex" substrings
      2. The presence of any Claude-specific environment variable
         (CLAUDE_PLUGIN_ROOT, CLAUDE_CODE_ENTRYPOINT)
      3. The presence of any Codex-specific environment variable
         (CODEX_HOME, CODEX_SANDBOX, CODEX_EXECUTION_MODE)
  - The first matching marker in this priority order determines the
    returned backend: "claude-cli" for Claude markers, "codex-cli" for
    Codex markers
  - When no marker matches, returns "codex-cli" (the default fallback)
  - The same input environment always produces the same output (pure
    function with respect to environment state at call time)

---

### Actual Behavior

The function returns a string or None according to these rules. Let env(k) denote the value of environment variable k, or None if k is absent. Let norm(v) be the canonical backend name when v is a recognized alias, otherwise v unchanged; norm(None)=None. The return value R is: if norm(env('FM_AGENT_MODEL_BACKEND')) != 'auto' then R = norm(env('FM_AGENT_MODEL_BACKEND')). Otherwise (that is, norm(env('FM_AGENT_MODEL_BACKEND')) == 'auto'), let hint = (env('FM_AGENT_HOST') or env('FM_AGENT_CLIENT') or '').lower(). Then if 'claude' in hint, R = 'claude-cli'; else if 'codex' in hint, R = 'codex-cli'; else if any env(v) is truthy for v in {'CLAUDE_PLUGIN_ROOT', 'CLAUDE_CODE_ENTRYPOINT'}, R = 'claude-cli'; else if any env(v) is truthy for v in {'CODEX_HOME', 'CODEX_SANDBOX', 'CODEX_EXECUTION_MODE'}, R = 'codex-cli'; else R = 'codex-cli'. The possible returned values are None (when FM_AGENT_MODEL_BACKEND is not set and norm(None) returns None) or a string, typically a canonical backend identifier ('opencode', 'codex-cli', 'claude-cli') but could be any string if FM_AGENT_MODEL_BACKEND was set to a non-canonical, non-alias value that was not 'auto'.

---

## Code Evidence

Line 2: backend = _normalize_backend(os.environ.get("FM_AGENT_MODEL_BACKEND"))
Line 3: if backend != "auto":
Line 4:     return backend

---

## Trigger Condition

When FM_AGENT_MODEL_BACKEND is not set, the code returns None because _normalize_backend(None) produces None, and the condition backend != 'auto' is true (None != 'auto'). The specification requires that when the variable is absent, it should fall through to auto-detection and return one of the three canonical backends, never None.

---

## How to trigger the bug

When `FM_AGENT_MODEL_BACKEND` is absent from the environment, `_normalize_backend(None)` returns `"opencode"` (because `(None or "")` → `""`, and `not ""` is `True` → `"opencode"`). The condition `backend != "auto"` is `True`, so the function returns `"opencode"` immediately without inspecting any environment markers. This violates the specification, which requires that when the variable is absent, the function should fall through to auto-detection and check Claude/Codex environment markers.

### Inputs

| Parameter | Value |
|-----------|-------|
| `FM_AGENT_MODEL_BACKEND` | (not set — absent from environment) |
| `CLAUDE_PLUGIN_ROOT` | `/tmp/test-claude-plugin-root` |

### Expected (spec-correct) Output

`"claude-cli"`

### Actual (buggy) Output

`"opencode"`

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import os
import sys
sys.path.insert(0, '.')

from src.cli_backend import resolve_model_backend, _normalize_backend

# Ensure FM_AGENT_MODEL_BACKEND is not set
os.environ.pop("FM_AGENT_MODEL_BACKEND", None)

# Set a Claude marker — auto-detection should find this if reached
os.environ["CLAUDE_PLUGIN_ROOT"] = "/tmp/test"

result = resolve_model_backend()
# actual (buggy) output: "opencode"
# expected (correct) output: "claude-cli"

# Root cause: _normalize_backend(None) returns "opencode",
# short-circuiting before auto-detection
print(_normalize_backend(None))  # "opencode"
```

---

## Probe Script

```python
"""Probe script for resolve_model_backend bug: when FM_AGENT_MODEL_BACKEND
is not set, the function returns "opencode" via _normalize_backend's
fallback instead of running auto-detection against environment markers.

Spec requirement: when FM_AGENT_MODEL_BACKEND is absent, the function
should inspect environment markers (CLAUDE_PLUGIN_ROOT, CODEX_HOME, etc.)
and return the corresponding backend. Setting a Claude marker like
CLAUDE_PLUGIN_ROOT should yield "claude-cli".

Actual (buggy) behavior: _normalize_backend(None) returns "opencode" because
(None or "") -> "", and not "" is True -> returns "opencode". Then the
condition backend != "auto" is True, so it returns "opencode" immediately
without checking any environment markers.
"""

import os
import sys

# Add repo root to path so 'src' package is importable.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Import the module. Note: load_dotenv() runs at import time; since no .env
# file exists in this snapshot, no env vars are modified.
from src.cli_backend import resolve_model_backend

# Ensure FM_AGENT_MODEL_BACKEND is NOT set (load_dotenv may have added it
# if a .env file existed, but here it does not).
os.environ.pop("FM_AGENT_MODEL_BACKEND", None)

# Set a Claude-specific marker so auto-detection would find it if reached.
os.environ["CLAUDE_PLUGIN_ROOT"] = "/tmp/test-claude-plugin-root"

try:
    actual = resolve_model_backend()

    # Per spec: when FM_AGENT_MODEL_BACKEND is absent, auto-detection should
    # see CLAUDE_PLUGIN_ROOT and return "claude-cli".
    expected = "claude-cli"

    # Bug confirmed when actual does NOT match expected.
    # The buggy code returns "opencode" (via _normalize_backend fallback)
    # instead of "claude-cli" (via auto-detection).
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
CONFIRMED — actual: 'opencode' | expected: 'claude-cli'
```

# Bug Report: _elp_argv

**Source file:** `src/languages/erlang.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

Returns a non-empty list of strings whose final element is "server", suitable for invoking ELP as a subprocess that reads JSON-RPC requests from standard input and writes JSON-RPC responses to standard output. The preceding elements form a platform-appropriate invocation of the configured ELP binary. The return value is stable: two calls return equal lists if the ELP backend configuration has not changed, and return unequal lists if the ELP backend has changed in a way that could produce different analysis output for the same input project.

---

### Actual Behavior

The function returns a list of strings representing the argument vector to launch the ELP server. Let `cmd = settings.erlang.command.strip()` and `tokens = shlex.split(cmd, posix=(os.name != 'nt'))`. If `tokens` is empty, let `base = ['elp']`; otherwise `base = tokens`. The returned list is `base + ['server']`. Consequently, the result is never empty, always has `'server'` as its last element, and its first element is either the stripped nonempty content of `settings.erlang.command` split into tokens or `'elp'` if no valid command was configured.

---

## Code Evidence

Line 62: `return [*argv, "server"]`

---

## Trigger Condition

The returned list becomes `['elp', 'server', 'server']`, which does not form a platform-appropriate invocation because the preceding elements now contain a duplicate 'server' that could confuse ELP. The specification requires that the arguments before the final 'server' constitute a correct invocation; the duplicate 'server' violates this requirement.

---

## How to trigger the bug

When `settings.erlang.command` is set to `"elp server"` (or any command that already includes the `"server"` subcommand), `_elp_argv()` unconditionally appends another `"server"` to the parsed argument vector, producing a duplicate.

### Inputs

| Parameter | Value |
|-----------|-------|
| `settings.erlang.command` | `"elp server"` |

### Expected (spec-correct) Output

`['elp', 'server']` — the command parsed from `settings.erlang.command`, which already provides the `"server"` subcommand.

### Actual (buggy) Output

`['elp', 'server', 'server']` — `"server"` is appended unconditionally, duplicating the one already present in the configured command.

### How to Reproduce

1. Navigate to the repo root.
2. Import `src.languages.erlang` and override `config.settings.erlang.command`:
```python
import config
from src.languages.erlang import _elp_argv

config.settings.erlang.command = "elp server"
result = _elp_argv()
# actual (buggy) output: ['elp', 'server', 'server']
# expected (correct) output: ['elp', 'server']
```

---

## Probe Script

```python
"""Probe for bug: _elp_argv unconditionally appends "server", creating a duplicate
when the ELP_COMMAND already includes the "server" subcommand.

Bug ID: src--languages--erlang-py--_elp_argv

Expected (spec): the final element is "server", and the preceding elements form
a platform-appropriate ELP invocation without a duplicate "server".

Actual (bug): the function blindly appends "server" to the parsed argv, so a
command like "elp server" produces ['elp', 'server', 'server'].
"""

import os
import sys
from pathlib import Path

# Ensure the repo root and src/ are importable (same pattern as other probes).
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_SRC = _REPO_ROOT / "src"
for p in (str(_REPO_ROOT), str(_SRC)):
    if p not in sys.path:
        sys.path.insert(0, p)

# Save and sanitize environment to isolate the test.
_saved_env = {k: os.environ.get(k) for k in (
    "ELP_COMMAND", "ELP_TIMEOUT_SECONDS", "FM_AGENT_CONFIG",
    "LLM_API_KEY", "LLM_API_BASE_URL", "FM_AGENT_MODEL_BACKEND",
    "LLM_MODEL", "LLM_EFFORT", "OPENCODE_MODEL_PROVIDER", "LLM_API_STYLE",
    "MAX_SPC_ITER", "GRANULARITY", "MAX_WORKERS", "OPENCODE_MAX_RETRIES",
    "BUG_VALIDATION_MAX_RETRIES", "OPENCODE_TIMEOUT_SECONDS",
    "FM_AGENT_DOMAIN_KNOWLEDGE",
)}
for k in _saved_env:
    if k in os.environ:
        del os.environ[k]

try:
    import config
    from languages.erlang import _elp_argv

    # --- Step 1: Default command (no server) — should work correctly ---
    config.settings.erlang.command = "elp"
    result_default = _elp_argv()
    assert result_default[-1] == "server", f"Expected last element to be 'server', got: {result_default}"
    assert result_default.count("server") == 1, (
        f"Default command should produce exactly one 'server', got: {result_default}"
    )

    # --- Step 2: Command already contains "server" subcommand ---
    # This is the trigger condition described in the bug report.
    # If a user configures ELP_COMMAND="elp server", the parsed argv already
    # contains "server", and appending another creates a duplicate.
    config.settings.erlang.command = "elp server"
    result_duplicate = _elp_argv()

    # The spec says the preceding elements should be a valid ELP invocation
    # without duplicate tokens. '["elp", "server", "server"]' is not valid.
    has_duplicate = result_duplicate.count("server") > 1

    if has_duplicate:
        expected_spec = ["elp", "server"]  # what a correct invocation would look like
        print(
            f"CONFIRMED — _elp_argv() returns a list with duplicate 'server': "
            f"actual: {result_duplicate!r} | "
            f"expected (no duplicate): {expected_spec!r}"
        )
    else:
        # If no duplicate, the function happened to produce a correct result
        # (e.g. shlex.split produced something unexpected).
        print(
            f"NOT CONFIRMED — no duplicate 'server' in result: {result_duplicate!r}"
        )

except Exception as e:
    import traceback
    traceback.print_exc()
    print(f"ERROR: {type(e).__name__}: {e}")

finally:
    # Restore environment
    for k, v in _saved_env.items():
        if v is not None:
            os.environ[k] = v
        elif k in os.environ:
            del os.environ[k]
```

### Probe Output

```
CONFIRMED — _elp_argv() returns a list with duplicate 'server': actual: ['elp', 'server', 'server'] | expected (no duplicate): ['elp', 'server']
```

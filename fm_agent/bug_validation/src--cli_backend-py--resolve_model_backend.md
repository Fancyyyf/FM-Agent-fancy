# Bug Report: resolve_model_backend

**Source file:** `/home/fancy/Projects_Vault/FM-Agent/fm_agent/extracted_functions/src/cli_backend-py/resolve_model_backend.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

Returns a non-empty string from the set {"codex-cli", "claude-cli", "opencode"} identifying which CLI backend is configured for use. When an explicit backend is configured (not "auto"), the canonical form of the configured backend name is returned. When the backend is configured to auto-detect, the return value identifies the first CLI backend detected as available in the current process environment, defaulting to "codex-cli" when no CLI backend is detected.

---

### Actual Behavior

Natural language: The function returns a string that resolves the model backend according to a priority scheme. First, it normalizes the configured backend from `settings.llm.backend` using `_normalize_backend`; if that canonical name is not `'auto'`, it is returned directly. Otherwise, it inspects environment variables: if either `FM_AGENT_HOST` or `FM_AGENT_CLIENT` (caseinsensitive) contains `'claude'`, the result is `'claude-cli'`; if it contains `'codex'`, the result is `'codex-cli'`. If no such hint is found, it checks for the presence of Claudespecific markers `CLAUDE_PLUGIN_ROOT` or `CLAUDE_CODE_ENTRYPOINT`  if any is set, the result is `'claude-cli'`. Failing that, it checks for Codex markers `CODEX_HOME`, `CODEX_SANDBOX`, or `CODEX_EXECUTION_MODE`  if any is set, the result is `'codex-cli'`. In the absence of any positive signal, the default return value is `'codex-cli'`. The function modifies no external state. Formal logic: Let `B = _normalize_backend(settings.llm.backend)`. Let `H = (getenv('FM_AGENT_HOST') OR getenv('FM_AGENT_CLIENT') OR '')` lowercased. Let `C = getenv('CLAUDE_PLUGIN_ROOT') OR getenv('CLAUDE_CODE_ENTRYPOINT')`. Let `X = getenv('CODEX_HOME') OR getenv('CODEX_SANDBOX') OR getenv('CODEX_EXECUTION_MODE')`. The return value `R` is defined as: `R = B` if `B  'auto'`; else if `'claude'  H` then `R = 'claude-cli'`; else if `'codex'  H` then `R = 'codex-cli'`; else if `C  ` then `R = 'claude-cli'`; else if `X  ` then `R = 'codex-cli'`; else `R = 'codex-cli'`. The environment is unchanged and `settings` is readonly.

---

## Code Evidence

Line 2: backend = _normalize_backend(settings.llm.backend)
Line 3: if backend != "auto":
Line 4:     return backend

---

## Trigger Condition

The specification requires the return value to be from the set {"codex-cli", "claude-cli", "opencode"}. However, when an explicit backend is configured (not "auto") and _normalize_backend does not map it to one of those allowed values, the code returns the normalized value unchanged. For example, with backend='unknown_backend', _normalize_backend returns 'unknown_backend', and the function returns it, violating the specification.

---

## How to trigger the bug

Describe the concrete inputs used in the probe, what the buggy code returns, and what the specification requires.

### Inputs

| Parameter | Value |
|-----------|-------|
| settings.llm.backend | "unknown_backend" |

### Expected (spec-correct) Output

Any value from `{"codex-cli", "claude-cli", "opencode"}`

### Actual (buggy) Output

`"unknown_backend"`

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
from config import settings
from src.cli_backend import resolve_model_backend

settings.llm.backend = "unknown_backend"
print(resolve_model_backend())
# actual (buggy) output: "unknown_backend"
# expected (correct) output: one of {"codex-cli", "claude-cli", "opencode"}
```

---

## Probe Script

```python
"""Probe script: confirm resolve_model_backend returns values outside the allowed set."""
import sys
import os

# Ensure the repo root is importable
_repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

ALLOWED_BACKENDS = {"codex-cli", "claude-cli", "opencode"}

try:
    from config import settings
    from src.cli_backend import resolve_model_backend

    # Inject an unrecognized backend value — per the spec, the function
    # must return one of the allowed backends, but the code returns the
    # normalized value unchanged for any unknown backend.
    settings.llm.backend = "unknown_backend"

    actual = resolve_model_backend()
    bug_reproduced = actual not in ALLOWED_BACKENDS
except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)

if bug_reproduced:
    print(f"CONFIRMED — actual: {actual!r} | allowed set: {ALLOWED_BACKENDS!r}")
else:
    print(f"NOT CONFIRMED — actual matched allowed set: {actual!r}")
```

### Probe Output

```
CONFIRMED — actual: 'unknown_backend' | allowed set: {'opencode', 'claude-cli', 'codex-cli'}
```

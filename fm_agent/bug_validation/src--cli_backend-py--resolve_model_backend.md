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
  - The returned backend is first determined by normalizing
    settings.llm.backend via _normalize_backend; if the result is not
    "auto", that result is returned immediately
  - When the normalized value of settings.llm.backend is "auto", the
    backend is determined by inspecting environment markers in a fixed
    priority order:
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
  - The same input (settings.llm.backend value and environment state)
    always produces the same output (pure function with respect to its
    inputs at call time)

---

### Actual Behavior

The function returns a string that is the canonical backend identifier resolved from the configuration and environment. Let normalized = _normalize_backend(settings.llm.backend). If normalized != 'auto', the result is normalized. Otherwise, when normalized == 'auto', let H = (os.environ.get('FM_AGENT_HOST') or os.environ.get('FM_AGENT_CLIENT') or '').lower(). If 'claude'  H or any of the environment variables CLAUDE_PLUGIN_ROOT or CLAUDE_CODE_ENTRYPOINT is set to a non-empty value, the result is 'claude-cli'. In all other cases (including when H contains 'codex' but not 'claude', when any of CODEX_HOME, CODEX_SANDBOX, or CODEX_EXECUTION_MODE is set, or when no environment hints are present), the result is 'codex-cli'.

---

## Code Evidence

Line 2:     backend = _normalize_backend(settings.llm.backend)
Line 3:     if backend != "auto":
Line 4:         return backend

---

## Trigger Condition

The specification requires the function to return one of the canonical backend identifiers 'opencode', 'codex-cli', or 'claude-cli'. The code returns the result of _normalize_backend unchanged when it is not 'auto'. According to the provided behaviour of _normalize_backend, if the input is not a recognised alias, it returns the input as-is. Therefore, for an input like 'foobar', the function returns 'foobar', which is not one of the allowed identifiers, violating the specification.

---

## How to trigger the bug

The bug occurs when `settings.llm.backend` is set to a value that is not a recognized alias in `_BACKEND_ALIASES` and is not `"auto"`. The `_normalize_backend` function passes such values through unchanged, and `resolve_model_backend` returns the unrecognized value directly — violating the spec's post-condition that only canonical identifiers are returned.

### Inputs

| Parameter | Value |
|-----------|-------|
| `settings.llm.backend` | `"foobar"` |

### Expected (spec-correct) Output

`one of "opencode", "codex-cli", or "claude-cli"`

### Actual (buggy) Output

`"foobar"`

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
from unittest.mock import patch
import config
from src.cli_backend import resolve_model_backend

with patch.object(config.settings.llm, "backend", "foobar"):
    result = resolve_model_backend()
    print(result)  # actual (buggy) output: 'foobar'
                   # expected (correct) output: one of 'opencode', 'codex-cli', 'claude-cli'
```

---

## Probe Script

```python
import sys
import os
from unittest.mock import patch

# The probe is run from the repo root, so cwd is the import base.
sys.path.insert(0, os.getcwd())


def main():
    try:
        import config
        from src.cli_backend import resolve_model_backend

        canonical = {"opencode", "codex-cli", "claude-cli"}
        # Monkey-patch settings.llm.backend to a non-canonical value
        with patch.object(config.settings.llm, "backend", "foobar"):
            actual = resolve_model_backend()
            # The spec requires a canonical identifier. The buggy code
            # passes the unrecognized value straight through.
            passed = actual not in canonical  # True = bug reproduced

        if passed:
            expected_fmt = f"one of {sorted(canonical)}"
            print(f"CONFIRMED — actual: {actual!r} | expected: {expected_fmt}")
        else:
            print(f"NOT CONFIRMED — actual matched expected: {actual!r}")

    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
```

### Probe Output

```
CONFIRMED — actual: 'foobar' | expected: one of ['claude-cli', 'codex-cli', 'opencode']
```

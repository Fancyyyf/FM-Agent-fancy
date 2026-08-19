# Bug Report: _stable_user_id

**Source file:** `/home/fancy/Projects_Vault/FM-Agent/fm_agent/extracted_functions/src/llm_client-py/_stable_user_id.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

Returns a non-empty string that identifies the current user. The returned value is stable: repeated calls within the same execution environment yield the same string. The value is the configured user identifier when set, or a built-in default identifier otherwise. The returned string is suitable for injection into LLM API request metadata for prompt-cache affinity.

---

### Actual Behavior

The function `_stable_user_id` is defined in the current namespace. It takes no arguments. When called, its return value is the result of evaluating `settings.inject.id or _DEFAULT_INJECT_USER_ID`.

---

## Code Evidence

Line 2:     return settings.inject.id or _DEFAULT_INJECT_USER_ID

---

## Trigger Condition

The function does not store the initial user ID; it reevaluates the setting on each call. Therefore, if settings.inject.id changes between calls, the returned string is not stable, violating the specification.

---

## How to trigger the bug

The function `_stable_user_id()` reads `settings.inject.id` on every call without caching or memoizing the first computed value. If `settings.inject.id` is mutated between calls — either directly via assignment or through a configuration reload — the returned user ID changes, violating the stability guarantee promised by the specification.

### Inputs

| Parameter | Value |
|-----------|-------|
| (none) | `_stable_user_id()` takes no arguments |

### Expected (spec-correct) Output

`"stable-user-or-session-id-xxxxxxx123"` (the default user ID, stable across all calls)

### Actual (buggy) Output

First call: `"stable-user-or-session-id-xxxxxxx123"` — after `settings.inject.id` is changed to `"altered-user-999"`, second call: `"altered-user-999"`

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import config
from src.llm_client import _stable_user_id

first = _stable_user_id()
# first -> "stable-user-or-session-id-xxxxxxx123"

config.settings.inject.id = "altered-user-999"
second = _stable_user_id()
# second -> "altered-user-999"  ← BUG: value changed, violating stability spec
# expected (correct) output: "stable-user-or-session-id-xxxxxxx123"
```

---

## Probe Script

```python
import sys
import os

# Ensure we import from the repo root (cwd for the probe runner).
sys.path.insert(0, os.getcwd())

try:
    import config
    from src.llm_client import _stable_user_id
except Exception as e:
    print(f"ERROR: import failed — {e}")
    sys.exit(1)

try:
    # Record initial state
    saved_id = config.settings.inject.id

    # First call: settings.inject.id defaults to "" (empty),
    # so _stable_user_id() should return _DEFAULT_INJECT_USER_ID.
    first = _stable_user_id()

    # Change settings.inject.id to a different value.
    config.settings.inject.id = "altered-user-999"

    # Second call: should now return the new value, NOT the original.
    second = _stable_user_id()

    # Restore original setting to keep the environment clean.
    config.settings.inject.id = saved_id

    # spec says: "stable — repeated calls within the same execution
    # environment yield the same string"
    # If first != second, the bug is confirmed.
    if first != second:
        print(
            f"CONFIRMED — first: {first!r} | second: {second!r} "
            f"| setting changed from {saved_id!r} to 'altered-user-999'"
        )
    else:
        print(
            f"NOT CONFIRMED — first: {first!r} | second: {second!r} "
            f"| values matched (function is stable)"
        )
except Exception as e:
    print(f"ERROR: {type(e).__name__}: {e}")
    sys.exit(1)
```

### Probe Output

```
CONFIRMED — first: 'stable-user-or-session-id-xxxxxxx123' | second: 'altered-user-999' | setting changed from '' to 'altered-user-999'
```

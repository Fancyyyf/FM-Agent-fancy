# Bug Report: _read_error_body

**Source file:** `/home/fancy/Projects_Vault/FM-Agent/fm_agent/extracted_functions/src/llm_client-py/_read_error_body.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

When the response body is readable and contains non-empty content, returns the body decoded as UTF-8 text, truncated to limit characters with a trailing ellipsis ("…") appended when the decoded text length exceeds limit. When the body is empty, unreadable, or reading raises an exception, returns None.

---

### Actual Behavior

The function returns a string value. Let R be the result of attempting exc.read() (ignoring exceptions). If exc.read() raises an exception, the function returns the empty string. Otherwise, if the bytes read are empty (falsey), the function returns the empty string. Otherwise, let T be the string obtained by decoding the bytes as UTF-8 with error replacement and stripping leading/trailing whitespace. The function then returns T[:limit] if len(T) <= limit, else T[:limit] + '…'. The HTTPError object's response body is consumed after a successful read; subsequent reads will return empty or raise.

---

## Code Evidence

Line 8: return ""
Line 10: return ""

---

## Trigger Condition

Condition A returns an empty string when reading raises an exception or the body is empty/falsey, but the specification requires returning None in all such cases (unreadable, empty, or exception).

---

## How to trigger the bug

Describe the concrete inputs used in the probe, what the buggy code returns, and what the specification requires.

### Inputs

| Parameter | Value |
|-----------|-------|
| exc (Case 1) | Mock HTTPError where `.read()` raises `OSError("simulated read failure")` |
| exc (Case 2) | Mock HTTPError where `.read()` returns `b""` (empty bytes) |
| limit | default (800) |

### Expected (spec-correct) Output

`None` (for both error and empty-body cases)

### Actual (buggy) Output

`""` (empty string, for both cases)

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
from src.llm_client import _read_error_body

class ReadRaises:
    def read(self):
        raise OSError("simulated")

class ReadEmpty:
    def read(self):
        return b""

# Both should return None per spec, but return ""
result1 = _read_error_body(ReadRaises())  # actual (buggy) output: ""
# expected (correct) output: None

result2 = _read_error_body(ReadEmpty())   # actual (buggy) output: ""
# expected (correct) output: None
```

---

## Probe Script

```python
"""Probe for bug: _read_error_body returns '' instead of None on error/empty."""

import sys
import tempfile
import os

# Per instructions: all fixtures and temp work stay in a fresh temp dir, not
# in the active fm_agent/ directory.
_workspace = tempfile.mkdtemp(prefix="probe_read_error_body_")

try:
    # Load via the public package entry point — import src.llm_client
    from src.llm_client import _read_error_body
except ImportError as e:
    print(f"ERROR: cannot import _read_error_body: {e}")
    sys.exit(1)

bugs_found = 0

# --- Case 1: exc.read() raises an exception ---
class _ReadRaisesExc:
    """Mock HTTPError whose read() always raises."""
    def read(self):
        raise OSError("simulated read failure")

try:
    result1 = _read_error_body(_ReadRaisesExc())
except Exception as e:
    print(f"ERROR: _read_error_body crashed on read-raising mock: {e}")
    sys.exit(1)

# Spec says: return None when reading raises an exception.
# Buggy code (line 8): returns ""
if result1 is not None and result1 == "":
    bugs_found += 1
    print(f"[CASE 1] BUG: read() raised → got {result1!r}, expected None")
elif result1 is None:
    print(f"[CASE 1] OK: read() raised → returned None (as spec requires)")
else:
    print(f"[CASE 1] UNEXPECTED: read() raised → got {result1!r}")

# --- Case 2: exc.read() returns empty bytes ---
class _ReadEmpty:
    """Mock HTTPError whose read() returns empty bytes."""
    def read(self):
        return b""

try:
    result2 = _read_error_body(_ReadEmpty())
except Exception as e:
    print(f"ERROR: _read_error_body crashed on empty-read mock: {e}")
    sys.exit(1)

# Spec says: return None when body is empty.
# Buggy code (line 10): returns ""
if result2 is not None and result2 == "":
    bugs_found += 1
    print(f"[CASE 2] BUG: read() returned empty → got {result2!r}, expected None")
elif result2 is None:
    print(f"[CASE 2] OK: read() returned empty → returned None (as spec requires)")
else:
    print(f"[CASE 2] UNEXPECTED: read() returned empty → got {result2!r}")

# --- Case 3 (negative control): exc.read() returns actual content ---
class _ReadContent:
    def read(self):
        return b"hello world"

try:
    result3 = _read_error_body(_ReadContent())
except Exception as e:
    print(f"ERROR: _read_error_body crashed on content mock: {e}")
    sys.exit(1)

# Spec says: returns decoded text. This should work either way.
print(f"[CASE 3] Content read → got {result3!r}")

# --- Case 4: content longer than limit ---
class _ReadLongContent:
    def read(self):
        return b"a" * 1000

try:
    result4 = _read_error_body(_ReadLongContent(), limit=10)
except Exception as e:
    print(f"ERROR: _read_error_body crashed on long-content mock: {e}")
    sys.exit(1)

print(f"[CASE 4] Long content (limit=10) → got {result4!r} (expects truncated + ellipsis)")

# --- Verdict ---
if bugs_found > 0:
    print(f"CONFIRMED — {bugs_found} case(s) return '' instead of None")
else:
    print("NOT CONFIRMED — function returns None as specified")

# Cleanup temp workspace
try:
    os.rmdir(_workspace)
except OSError:
    pass
```

### Probe Output

```
[CASE 1] BUG: read() raised → got '', expected None
[CASE 2] BUG: read() returned empty → got '', expected None
[CASE 3] Content read → got 'hello world'
[CASE 4] Long content (limit=10) → got 'aaaaaaaaaa…' (expects truncated + ellipsis)
CONFIRMED — 2 case(s) return '' instead of None
```

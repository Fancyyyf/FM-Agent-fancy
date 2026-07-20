# Bug Report: _matches_inject_target

**Source file:** `src/llm_client.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- When target is an absolute URL prefix, returns True if and only if url begins with target as a string prefix  covering all paths at or beneath the target's path hierarchy
  - When target is a hostname, returns True if and only if the hostname that url refers to is either exactly equal to target, or is a subdomain of target (the hostname ends with a period followed by target)
  - Returns False when url does not satisfy either matching rule  including when url refers to a hostname unrelated to target, or when url cannot be resolved to a hostname while target is a hostname

---

### Actual Behavior

The function returns a boolean. If the lowercased target starts with 'http://' or 'https://', the result is url.startswith(target) (case-sensitive). Otherwise, if parsing the URL with urllib.parse.urlparse raises any exception, the result is False. If no exception occurs, let host be the extracted hostname (or the empty string if hostname is None); the result is True if host equals target exactly, or if host ends with '.' + target; otherwise False. Formally, let R be the return value. Then (target.lower().startswith(('http://', 'https://'))  R = url.startswith(target))  (target.lower().startswith(('http://', 'https://'))  (exception during urllib.parse.urlparse(url)  R = False)  (no exception  R  (host == target  host.endswith('.' + target)) with host = (urllib.parse.urlparse(url).hostname or ''))). The function has no side effects.

---

## Code Evidence

Line 2: if target.lower().startswith(('http://', 'https://')):

---

## Trigger Condition

The code only treats targets starting with 'http://' or 'https://' as absolute URL prefixes. Other valid URL schemes (e.g., 'ftp://') are not handled as absolute URL prefixes, causing the function to incorrectly perform hostname matching instead of string prefix matching. For target='ftp://example.com/' and url='ftp://example.com/file', the code returns False, but the specification requires True because url begins with the absolute URL prefix target.

---

## How to trigger the bug

The function is exercised through `_should_inject_user_id`, the smallest public wrapper that calls `_matches_inject_target` for each target configured via the `INJECT_HOST` environment variable.

### Inputs

| Parameter | Value |
|-----------|-------|
| url | `"ftp://example.com/file"` |
| target (via INJECT_HOST) | `"ftp://example.com/"` |

### Expected (spec-correct) Output

`True` — the url `"ftp://example.com/file"` begins with the absolute URL prefix `"ftp://example.com/"`, so the spec requires True.

### Actual (buggy) Output

`False` — the code only recognizes `http://` and `https://` as absolute URL prefixes. The `ftp://` target falls through to hostname matching, where `host = "example.com"` does not equal `"ftp://example.com/"` and does not match any subdomain rule.

### How to Reproduce

1. Navigate to the repo root.
2. Run the following snippet:

```python
import os
os.environ["INJECT_HOST"] = "ftp://example.com/"
from src.llm_client import _matches_inject_target
_matches_inject_target("ftp://example.com/file", "ftp://example.com/")
# actual (buggy) output: False
# expected (correct) output: True
```

---

## Probe Script

```python
"""Probe script for bug: _matches_inject_target only treats http:// and https://
as absolute URL prefixes; other schemes (e.g., ftp://) incorrectly fall through
to hostname matching."""

import sys
import os

# Allow imports from the repo root (package entry point).
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

try:
    # Set target to an ftp:// URL prefix via INJECT_HOST so _inject_targets()
    # picks it up, then exercise _matches_inject_target through the smallest
    # public wrapper: _should_inject_user_id.
    os.environ["INJECT_HOST"] = "ftp://example.com/"
    from src.llm_client import _should_inject_user_id

    actual = _should_inject_user_id("ftp://example.com/file")
    # Specification requires True: the url begins with the absolute URL prefix target.
    expected = True
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
CONFIRMED — actual: False | expected: True
```

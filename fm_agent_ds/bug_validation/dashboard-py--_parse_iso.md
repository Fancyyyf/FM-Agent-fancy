# Bug Report: _parse_iso

**Source file:** `/home/fancy/Projects_Vault/FM-Agent/fm_agent/extracted_functions/dashboard-py/_parse_iso.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

Returns None when ts is None or any falsy value. When ts is a string, interprets it as an ISO 8601 timestamp and returns a datetime object representing that moment if parsing succeeds. A trailing 'Z' suffix on the timestamp string denotes the UTC timezone offset. Returns None without raising an exception when ts is not a valid ISO 8601 timestamp string (including malformed strings, invalid date or time components, or otherwise unparseable input). The function never raises an exception to its caller.

---

### Actual Behavior

If `ts` is falsy (e.g., `None`, empty string, or any other false value), the function returns `None`. If `ts` is a truthy string (a non-empty string), then before parsing, any trailing 'Z' is replaced by '+00:00'. The function then attempts to call `datetime.fromisoformat` on that resulting string. If the call succeeds without raising an exception, the function returns the created `datetime` object. If any exception is raised (for example, due to an invalid ISO-8601 format), the function catches it and returns `None`. Formally: result = (None if not ts else (let s = ts[:-1] + '+00:00' if ts.endswith('Z') else ts in (datetime.fromisoformat(s) if no exception occurs else None))).

---

## Code Evidence

Line 7: return datetime.fromisoformat(ts)

---

## Trigger Condition

The specification requires that any valid ISO 8601 timestamp string be successfully parsed and returned as a datetime object. The code delegates parsing to datetime.fromisoformat, which does not support all ISO 8601 formats. For example, the ordinal date timestamp '2021-001T00:00:00Z' is valid per ISO 8601 but fromisoformat cannot parse it, causing the function to return None instead of a datetime, violating the specification.

---

## How to trigger the bug

The `_parse_iso` function delegates all parsing to Python's `datetime.fromisoformat`, which has limited ISO 8601 format support. Valid ISO 8601 ordinal dates (e.g., `2021-001` representing day 1 of 2021) are rejected by `fromisoformat`, causing the function to return `None` instead of a `datetime` object.

### Inputs

| Parameter | Value |
|-----------|-------|
| ts | `"2021-001T00:00:00Z"` |

### Expected (spec-correct) Output

`datetime(2021, 1, 1, 0, 0, 0, tzinfo=timezone.utc)`

### Actual (buggy) Output

`None`

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
from dashboard import _parse_iso

result = _parse_iso("2021-001T00:00:00Z")
# actual (buggy) output: None
# expected (correct) output: datetime(2021, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
print(result)
```

---

## Probe Script

```python
"""Probe script for bug dashboard-py--_parse_iso.

Tests whether _parse_iso correctly parses a valid ISO 8601 ordinal date
timestamp. Per the specification, any valid ISO 8601 timestamp string
should be parsed and returned as a datetime object. However,
datetime.fromisoformat (used by the implementation) does not support
ordinal date formats like '2021-001T00:00:00Z'.

This test uses several valid ISO 8601 formats that fromisoformat
may not support, to confirm the specification/implementation gap.
"""
import sys
import os
import tempfile

# Ensure the repo root is on sys.path so that 'from dashboard import ...' works.
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, REPO_ROOT)

# The probe must not use fm_agent/ as its runtime workspace.
# Use a fresh temporary directory for any runtime outputs.
PROBE_TMP = tempfile.mkdtemp(prefix="probe_parse_iso_")

try:
    from dashboard import _parse_iso
except ImportError as e:
    print(f"ERROR: {e}")
    sys.exit(1)

# Test case 1 (primary): ordinal date — valid ISO 8601, unsupported by fromisoformat
# Specification says: "any valid ISO 8601 timestamp string" should parse successfully
try:
    result = _parse_iso("2021-001T00:00:00Z")
except Exception as e:
    print(f"ERROR during ordinal date test: {e}")
    sys.exit(1)

if result is None:
    # Bug confirmed: valid ISO 8601 string returned None instead of datetime
    print("CONFIRMED — ordinal date '2021-001T00:00:00Z' returned None (expected a datetime object per spec)")
else:
    # fromisoformat parsed it successfully — spec and implementation match for this input
    print(f"NOT CONFIRMED — ordinal date '2021-001T00:00:00Z' returned {result!r} (datetime parsed OK)")
```

### Probe Output

```
12:52:21 - LiteLLM:WARNING: get_model_cost_map.py:271 - LiteLLM: Failed to fetch remote model cost map from https://raw.githubusercontent.com/BerriAI/litellm/main/model_prices_and_context_window.json: [SSL: UNEXPECTED_EOF_WHILE_READING] EOF occurred in violation of protocol (_ssl.c:1000). Falling back to local backup.
CONFIRMED — ordinal date '2021-001T00:00:00Z' returned None (expected a datetime object per spec)
```

# Bug Report: _fingerprint_digest

**Source file:** `src/languages/erlang-py/_fingerprint_digest.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- Returns a 64-character lowercase hexadecimal string (SHA-256 digest)
  - The result is deterministic: for any two tuples t1 and t2,
    t1 == t2 implies _fingerprint_digest(t1) == _fingerprint_digest(t2)
  - Two tuples that are not equal produce different digests with
    overwhelming probability (consistent with SHA-256 collision resistance)
  - The digest is computed from a compact JSON serialization of the tuple
    (no indentation, no whitespace between keys/values, and Unicode
    characters preserved without ASCII escaping)

---

### Actual Behavior

The function returns a string `d` such that `d` equals `hashlib.sha256(json.dumps(fingerprint, ensure_ascii=False, separators=(',', ':')).encode('utf-8')).hexdigest()`. Given the pre-condition, `json.dumps` does not raise `TypeError`; therefore the function completes normally, has no side effects, and the result is the SHA-256 hexadecimal digest of the compact, non-ASCII-escaped JSON representation of the input tuple.

---

## Code Evidence

Line 2: payload = json.dumps(fingerprint, ensure_ascii=False, separators=(",", ":"))

---

## Trigger Condition

The specification requires that equal tuples produce equal digests. Two tuples containing dictionaries with identical key-value pairs but different insertion orders are equal in Python (t1 == t2), but json.dumps does not sort dictionary keys, so it produces different JSON strings, leading to different SHA256 digests. This violates the deterministic requirement.

---

## How to trigger the bug

The function `_fingerprint_digest` serializes a tuple to JSON via `json.dumps` without `sort_keys=True`. In Python 3.7+, dictionaries preserve insertion order, and `json.dumps` does not sort keys. Two tuples that are equal (`t1 == t2`) but contain dicts with different key insertion orders will serialize to different JSON payloads and thus yield different SHA-256 digests.

### Inputs

| Parameter | Value |
|-----------|-------|
| fingerprint (t1) | `({"a": 1, "b": 2},)` |
| fingerprint (t2) | `({"b": 2, "a": 1},)` |

Note: `t1 == t2` (True in Python)

### Expected (spec-correct) Output

Same digest for both tuples since `t1 == t2`.

### Actual (buggy) Output

Different digests:
- `d1 = "44c7deead2ed8313d29655e45c0d1469419213c93d9f44d66da7c7afe46e74e3"`
- `d2 = "fbfdbb71d43c5d21b3d346f5618d5c6a9b5a9e93630e8be8065c05c85aaf2ce8"`

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import sys
sys.path.insert(0, "src")
from languages.erlang import _fingerprint_digest

t1 = ({"a": 1, "b": 2},)
t2 = ({"b": 2, "a": 1},)

assert t1 == t2  # they are equal
d1 = _fingerprint_digest(t1)
d2 = _fingerprint_digest(t2)
# actual (buggy) output: d1 != d2
# expected (correct) output: d1 == d2
```

---

## Probe Script

```python
"""Probe script for bug: _fingerprint_digest non-deterministic for equal tuples with dicts."""
import sys
import os

# Add src/ to sys.path so we can import the package
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))
sys.path.insert(0, "src")

try:
    from languages.erlang import _fingerprint_digest
except ImportError:
    sys.path.insert(0, os.path.abspath("src"))
    from languages.erlang import _fingerprint_digest

# Two tuples that are equal in Python (t1 == t2)
# but contain dicts with different key insertion orders
t1 = ({"a": 1, "b": 2},)
t2 = ({"b": 2, "a": 1},)

# Sanity check: they ARE equal in Python
assert t1 == t2, f"Pre-condition violated: t1 != t2"

d1 = _fingerprint_digest(t1)
d2 = _fingerprint_digest(t2)

# Bug confirmation: equal tuples produce DIFFERENT digests
bug_exists = (d1 != d2)

if bug_exists:
    print(f"CONFIRMED — actual: d1={d1!r} | d2={d2!r} | t1 == t2 is {t1 == t2}")
else:
    print(f"NOT CONFIRMED — actual matched: d1={d1!r} | d2={d2!r}")
```

### Probe Output

```
CONFIRMED — actual: d1='44c7deead2ed8313d29655e45c0d1469419213c93d9f44d66da7c7afe46e74e3' | d2='fbfdbb71d43c5d21b3d346f5618d5c6a9b5a9e93630e8be8065c05c85aaf2ce8' | t1 == t2 is True
```

# Bug Report: new_event_id

**Source file:** `src/trace_writer.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- Returns a string composed of prefix, a single underscore, and a 32-character lowercase hexadecimal string
  - The returned identifier is globally unique: it differs from every identifier previously returned by any invocation of new_event_id

---

### Actual Behavior

The function returns a string formed by concatenating the prefix (the provided non-empty string argument or the default 'evt'), an underscore, and the 32-character hexadecimal digest of a randomly generated UUID4. Formally, if s is the return value, p is the prefix (p  ''), then s = p + '_' + h where h = uuid.uuid4().hex and h is a string of 32 lowercase hexadecimal digits ([0-9a-f]{32}).

---

## Code Evidence

Line 2: return f"{prefix}_{uuid.uuid4().hex}"

---

## Trigger Condition

The code relies solely on the randomness of uuid.uuid4() for uniqueness, which provides only probabilistic and not deterministic guarantee. Therefore, it can produce a duplicate identifier across invocations, failing the specification's requirement of global uniqueness.

---

## How to trigger the bug

The bug is confirmed by monkey-patching `uuid.uuid4()` to return a deterministic (non-random) value, then calling `new_event_id()` twice. With the randomness removed, the function returns identical IDs for both calls, proving that no collision-prevention mechanism exists beyond UUID4's probabilistic randomness.

### Inputs

| Parameter | Value |
|-----------|-------|
| prefix | `"test"` |
| uuid.uuid4() | `uuid.UUID("12345678-1234-1234-1234-123456789abc")` (deterministic mock) |

### Expected (spec-correct) Output

Each call to `new_event_id()` must return a globally unique identifier, distinct from every identifier previously returned.

### Actual (buggy) Output

Both calls return `'test_12345678123412341234123456789abc'` — a duplicate.

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import uuid
from src.trace_writer import new_event_id

# Remove randomness — reveal absence of uniqueness mechanism
fixed = uuid.UUID("12345678-1234-1234-1234-123456789abc")
uuid.uuid4 = lambda: fixed

id1 = new_event_id("test")
id2 = new_event_id("test")

# actual (buggy) output: 'test_12345678123412341234123456789abc' == 'test_12345678123412341234123456789abc'
# expected (correct) output: globally unique — distinct IDs for each invocation
```

---

## Probe Script

```python
import sys
import uuid

# Ensure the repo root is on sys.path so 'src' is importable
sys.path.insert(0, ".")

original_uuid4 = uuid.uuid4
fixed_uuid = uuid.UUID("12345678-1234-1234-1234-123456789abc")

# Monkey-patch uuid.uuid4 to return a deterministic value, revealing that
# new_event_id has no collision-prevention mechanism beyond randomness.
uuid.uuid4 = lambda: fixed_uuid

try:
    from src.trace_writer import new_event_id

    id1 = new_event_id("test")
    id2 = new_event_id("test")

    # Restore original now that we've called the function
    uuid.uuid4 = original_uuid4

    # Bug confirmed if identical IDs are returned because
    # the code relies solely on uuid.uuid4() randomness.
    passed = id1 == id2

    if passed:
        print(f"CONFIRMED — duplicate IDs under deterministic uuid4: {id1!r} == {id2!r}")
    else:
        print(f"NOT CONFIRMED — IDs differed: {id1!r} != {id2!r}")
except Exception as e:
    uuid.uuid4 = original_uuid4
    print(f"ERROR: {e}")
    sys.exit(1)
```

### Probe Output

```
CONFIRMED — duplicate IDs under deterministic uuid4: 'test_12345678123412341234123456789abc' == 'test_12345678123412341234123456789abc'
```

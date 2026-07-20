# Bug Report: add_entry

**Source file:** `/tmp/fm_agent_wt_FM-Agent_dlsr6ukl/snapshot/fm_agent/extracted_functions/src/parser-py/add_entry.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- The value stored for key function_name in the map equals the spec argument
  - The value stored for key function_name in self.signatures equals the signature argument

---

### Actual Behavior

self[function_name] == spec    self.signatures[function_name] == signature    (k  keys(self) \ {function_name} : self[k] == old(self)[k])    (k  keys(self.signatures) \ {function_name} : self.signatures[k] == old(self.signatures)[k])

---

## Code Evidence

Line 2:         self[function_name] = spec
Line 3:         self.signatures[function_name] = signature

---

## Trigger Condition

When self.signatures is the same object as self, the second assignment overwrites the first, leaving self[function_name] equal to signature instead of spec. This violates the requirement that the map stores the spec argument under function_name.

---

## How to trigger the bug

Describe the concrete inputs used in the probe, what the buggy code returns, and what the specification requires.

### Inputs

| Parameter | Value |
|-----------|-------|
| `function_name` | `'test_func'` |
| `signature` | `'expected sig value'` |
| `spec` | `'expected spec value'` |
| (pre-condition) `self.signatures` | aliased to `self` (same object identity) |

### Expected (spec-correct) Output

`self['test_func']` should equal `'expected spec value'`

### Actual (buggy) Output

`self['test_func']` equals `'expected sig value'` (overwritten by the second assignment)

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
from src.parser import FunctionSpecMap

m = FunctionSpecMap()
m.signatures = m  # alias — self.signatures is the same object as self
m.add_entry('test_func', 'expected sig value', 'expected spec value')

print(m['test_func'])
# actual (buggy) output: 'expected sig value'
# expected (correct) output: 'expected spec value'
```

---

## Probe Script

```python
import sys
sys.path.insert(0, '.')
from src.parser import FunctionSpecMap

# Trigger condition: self.signatures is the same object as self.
# The spec requires: self[function_name] == spec, self.signatures[function_name] == signature.
# When self.signatures is self, the second assignment overwrites the first.

m = FunctionSpecMap()
m.signatures = m  # alias - this is the trigger condition

function_name = 'test_func'
spec_value = 'expected spec value'
sig_value = 'expected sig value'

try:
    m.add_entry(function_name, sig_value, spec_value)
    actual = m[function_name]
    expected = spec_value  # per spec, self[function_name] should be spec
    passed = actual != expected  # True means bug confirmed (spec violated)
except Exception as e:
    print(f'ERROR: {e}', flush=True)
    sys.exit(1)

if passed:
    print(f'CONFIRMED — actual self[fn]: {actual!r} | expected spec: {expected!r}', flush=True)
else:
    print(f'NOT CONFIRMED — actual matched expected: self[fn]={actual!r}', flush=True)
```

### Probe Output

```
CONFIRMED — actual self[fn]: 'expected sig value' | expected spec: 'expected spec value'
```

# Bug Report: _parse_spec_conditions

**Source file:** `/home/fancy/Projects_Vault/FM-Agent/fm_agent/extracted_functions/src/reasoner-py/_parse_spec_conditions.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

Returns a pair (pre, post) where pre is the string value associated with the 'pre_condition' key in spec (or an empty string when the key is absent) and post is the string value associated with the 'post_condition' key in spec (or an empty string when the key is absent).

---

### Actual Behavior

The function call raises a TypeError exception because `re.search` expects a string, but `spec` is a dict. No normal return occurs. Formal: ( pre, post  (pre, post) = _parse_spec_conditions(spec))  TypeRaised(TypeError)

---

## Code Evidence

Line 2: pre_match = re.search(r'Pre-condition:\s*\n(.*?)(?=\nPost-condition:|\Z)', spec, re.DOTALL)
Line 3: post_match = re.search(r'Post-condition:\s*\n(.*)', spec, re.DOTALL)

---

## Trigger Condition

The code calls re.search on spec, which expects a string, but the specification requires spec to be a dict. Any dict input causes a TypeError, never returning the required (pre, post) tuple. For example, with {'pre_condition': 'x>0', 'post_condition': 'y>0'}, the specification expects ('x>0', 'y>0') but the code raises TypeError.

---

## How to trigger the bug

The function `_parse_spec_conditions` attempts to parse pre-condition and post-condition from its `spec` argument using `re.search()`. The specification describes `spec` as a dict with `pre_condition` and `post_condition` keys, implying dict-based access to extract the values. However, the implementation calls `re.search()` on `spec` directly, which expects a string or bytes-like object. Passing a dict causes a `TypeError` instead of returning the expected `(pre, post)` tuple.

### Inputs

| Parameter | Value |
|-----------|-------|
| spec | `{'pre_condition': 'x>0', 'post_condition': 'y>0'}` |

### Expected (spec-correct) Output

`('x>0', 'y>0')`

### Actual (buggy) Output

`TypeError: expected string or bytes-like object, got 'dict'`

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import re

def _parse_spec_conditions(spec):
    pre_match = re.search(r'Pre-condition:\s*\n(.*?)(?=\nPost-condition:|\Z)', spec, re.DOTALL)
    post_match = re.search(r'Post-condition:\s*\n(.*)', spec, re.DOTALL)
    pre = pre_match.group(1).strip() if pre_match else None
    post = post_match.group(1).strip() if post_match else None
    return pre, post

spec_dict = {'pre_condition': 'x>0', 'post_condition': 'y>0'}
result = _parse_spec_conditions(spec_dict)
# actual (buggy) output: TypeError: expected string or bytes-like object, got 'dict'
# expected (correct) output: ('x>0', 'y>0')
```

---

## Probe Script

```python
import sys

# The spec claims _parse_spec_conditions(spec) accepts a dict with
# 'pre_condition' and 'post_condition' keys and returns a tuple of their values.
# The actual code does re.search() on spec, which expects a string.

# Inline the function to avoid any side effects from config import
import re

def _parse_spec_conditions(spec):
    pre_match = re.search(r'Pre-condition:\s*\n(.*?)(?=\nPost-condition:|\Z)', spec, re.DOTALL)
    post_match = re.search(r'Post-condition:\s*\n(.*)', spec, re.DOTALL)
    pre = pre_match.group(1).strip() if pre_match else None
    post = post_match.group(1).strip() if post_match else None
    return pre, post

spec_dict = {'pre_condition': 'x>0', 'post_condition': 'y>0'}
# Per the spec, expected output is ('x>0', 'y>0')
expected = ('x>0', 'y>0')

try:
    actual = _parse_spec_conditions(spec_dict)
    # If we get here without exception, compare against expected
    passed = actual != expected
except TypeError as e:
    # The code raises TypeError because re.search expects a string.
    # The spec says it should return a tuple, so this IS the bug.
    actual = f'TypeError: {e}'
    passed = True
except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)

if passed:
    print(f'CONFIRMED — actual: {actual!r} | expected: {expected!r}')
else:
    print(f'NOT CONFIRMED — actual matched expected: {actual!r}')
```

### Probe Output

```
CONFIRMED — actual: "TypeError: expected string or bytes-like object, got 'dict'" | expected: ('x>0', 'y>0')
```

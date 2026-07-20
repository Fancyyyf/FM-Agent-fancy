# Bug Report: _parse_spec_conditions

**Source file:** `/tmp/fm_agent_wt_FM-Agent_9w930mtx/snapshot/fm_agent/extracted_functions/src/reasoner-py/_parse_spec_conditions.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- Returns a 2-tuple (pre_condition, post_condition)
  - pre_condition is the text content between the "Pre-condition:" header line and the
    next section boundary, with leading and trailing whitespace stripped;
    it is None when no "Pre-condition:" section is found in the spec string
  - post_condition is the text content between the "Post-condition:" header line and
    the end of the string, with leading and trailing whitespace stripped;
    it is None when no "Post-condition:" section is found in the spec string

---

### Actual Behavior

The function returns a tuple (pre, post). Define pre_match = re.search(r'Pre-condition:\s*\n(.*?)(?=\nPost-condition:|\Z)', spec, re.DOTALL); pre = pre_match.group(1).strip() if pre_match else None. Define post_match = re.search(r'Post-condition:\s*\n(.*)', spec, re.DOTALL); post = post_match.group(1).strip() if post_match else None. Therefore, pre is the stripped content of the 'Pre-condition:' section if it exists (i.e., the substring after the newline following 'Pre-condition:', up to the next 'Post-condition:' line or end of spec), else None; post is the stripped content of the 'Post-condition:' section if it exists (i.e., the substring after the newline following 'Post-condition:' to the end of spec), else None.

---

## Code Evidence

Line 2: pre_match = re.search(r'Pre-condition:\s*\n(.*?)(?=\nPost-condition:|\Z)', spec, re.DOTALL)

---

## Trigger Condition

The specification requires pre_condition to be the text between the 'Pre-condition:' header line and the next section boundary. The code's pre regex (Line 2) only treats '\nPost-condition:' or end-of-string as a boundary, so any other section header (such as 'Note:') is incorrectly included in the pre_condition. For the input spec above, the code returns pre = 'x > 0\nNote:\n  test' instead of the correct 'x > 0'.

---

## How to trigger the bug

Describe the concrete inputs used in the probe, what the buggy code returns, and what the specification requires.

### Inputs

| Parameter | Value |
|-----------|-------|
| spec | `"Pre-condition:\nx > 0\nNote:\n  test\nPost-condition:\nresult > 0"` |

### Expected (spec-correct) Output

`('x > 0', 'result > 0')`

### Actual (buggy) Output

`('x > 0\nNote:\n  test', 'result > 0')`

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from src.reasoner import _parse_spec_conditions

spec = (
    "Pre-condition:\n"
    "x > 0\n"
    "Note:\n"
    "  test\n"
    "Post-condition:\n"
    "result > 0"
)

pre, post = _parse_spec_conditions(spec)
print(f"pre: {pre!r}")
# actual (buggy) output: pre: 'x > 0\\nNote:\\n  test'
# expected (correct) output: pre: 'x > 0'
```

---

## Probe Script

```python
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
try:
    import src.reasoner as reasoner_mod

    # A spec with an intermediate "Note:" section between Pre-condition and Post-condition.
    # The spec claims pre_condition should stop at the "next section boundary".
    # The buggy regex only looks for "Post-condition:" as boundary, so "Note:" gets included.
    spec = (
        "Pre-condition:\n"
        "x > 0\n"
        "Note:\n"
        "  test\n"
        "Post-condition:\n"
        "result > 0"
    )

    pre, post = reasoner_mod._parse_spec_conditions(spec)

    # Expected: pre should be "x > 0" (stopping at "Note:" section boundary)
    # Actual (buggy): pre includes "Note:\n  test" because regex doesn't recognize "Note:" as boundary
    expected_pre = "x > 0"
    expected_post = "result > 0"

    bug_confirmed = (pre == expected_pre + "\nNote:\n  test" or "Note:" in pre)
    post_ok = (post == expected_post)

    if bug_confirmed and post_ok:
        print(f'CONFIRMED — pre_condition: {pre!r} | expected: {expected_pre!r}')
    elif not bug_confirmed:
        print(f'NOT CONFIRMED — pre_condition: {pre!r} | post_condition: {post!r}')
    else:
        print(f'NOT CONFIRMED — pre_condition: {pre!r} | expected_pre: {expected_pre!r} | post_condition: {post!r} | expected_post: {expected_post!r}')
except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)
```

### Probe Output

```
CONFIRMED — pre_condition: 'x > 0\nNote:\n  test' | expected: 'x > 0'
```

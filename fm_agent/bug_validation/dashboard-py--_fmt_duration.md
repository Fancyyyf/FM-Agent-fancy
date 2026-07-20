# Bug Report: _fmt_duration

**Source file:** `/tmp/fm_agent_wt_FM-Agent_dlsr6ukl/snapshot/fm_agent/extracted_functions/dashboard-py/_fmt_duration.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- When seconds is None, returns the literal string "—" (U+2014 EM DASH)
  - When seconds is not None, returns a string composed of up to three
    space-separated segments ordered by decreasing time-unit magnitude
    (hours, then minutes, then seconds), where each segment has the form
    "<value><unit-suffix>" with unit-suffix in {"h", "m", "s"}:
    * The hour segment ("<H>h") appears only when floor(seconds) >= 3600;
      its value is the whole-hour count, never zero-padded
    * The minute segment ("<M>m" or "<MM>m") appears when
      floor(seconds) >= 60; its value is zero-padded to two digits only
      when the hour segment is present, otherwise it is the bare
      whole-minute count
    * The second segment ("<S>s" or "<SS>s") always appears; its value is
      zero-padded to two digits when any higher-magnitude segment is
      present, otherwise it is the bare whole-second count
  - All segment values (H, M, S) are derived from the integer part of
    seconds (fractional seconds are truncated via floor)

---

### Actual Behavior

If the input 'seconds' is None, the function returns the string '—'. If 'seconds' is a non-negative numeric value, let s = int(seconds) (truncation toward zero), h = s // 3600, m = (s % 3600) // 60, sec = s % 60. Then the return value is: if h > 0, return f'{h}h {m:02d}m {sec:02d}s'; if h == 0 and m > 0, return f'{m}m {sec:02d}s'; otherwise (h == 0 and m == 0) return f'{sec}s'. The function always returns a string and does not raise exceptions for inputs satisfying the pre-condition.

---

## Code Evidence

Line 4:     s = int(seconds)
Line 7:     if h:

---

## Trigger Condition

The code uses int(seconds) which truncates toward zero, while the specification requires truncation via floor (floor(seconds)). For negative seconds, these differ. For example, with seconds=-1.2, int(-1.2) = -1, but floor(-1.2) = -2. The code then computes h = -1 and enters the hour formatting branch (because if h: is true), returning '-1h 59m 59s'. The specification requires floor(-1.2) = -2, so no hour or minute segment, yielding '-2s'. This violates the output format and value.

---

## How to trigger the bug

The code uses `int(seconds)` (truncation toward zero) instead of `math.floor(seconds)` (truncation toward negative infinity). For negative input values, this produces a different integer value, which cascades into an incorrect formatted output. Additionally, the condition `if h:` is truthy for negative `h` values, whereas the specification requires the hour segment only when `floor(seconds) >= 3600`.

### Inputs

| Parameter | Value |
|-----------|-------|
| seconds | -1.2 |

### Expected (spec-correct) Output

`'-2s'`

### Actual (buggy) Output

`'-1h 59m 59s'`

### How to Reproduce

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
from dashboard import _fmt_duration
print(_fmt_duration(-1.2))
# actual (buggy) output: '-1h 59m 59s'
# expected (correct) output: '-2s'
```

---

## Probe Script

```python
import sys
import os
import math

# Ensure the repo root is on the path so `import dashboard` works
# probe is at fm_agent/bug_validation/ — go up 3 levels to repo root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

try:
    from dashboard import _fmt_duration

    # Trigger input: negative seconds where int() and math.floor() diverge.
    # int(-1.2) = -1, but floor(-1.2) = -2.
    actual = _fmt_duration(-1.2)

    # Spec-correct behavior (using math.floor as the spec requires):
    # floor(-1.2) = -2, which is < 60, so just the bare second segment.
    expected = f"{math.floor(-1.2)}s"   # '-2s'

    passed = actual != expected
    if passed:
        print(f'CONFIRMED — actual: {actual!r} | expected: {expected!r}')
    else:
        print(f'NOT CONFIRMED — actual matched expected: {actual!r}')
except Exception as e:
    print(f'ERROR: {e}')
    import traceback
    traceback.print_exc()
    sys.exit(1)
```

### Probe Output

```
CONFIRMED — actual: '-1h 59m 59s' | expected: '-2s'
```

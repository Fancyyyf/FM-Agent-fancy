# Bug Report: _symbol_line_span

**Source file:** `/tmp/fm_agent_wt_FM-Agent_dlsr6ukl/snapshot/fm_agent/extracted_functions/src/languages/erlang-py/_symbol_line_span.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- Returns a tuple (start, end) where both values are non-negative 0-based
    integers and start <= end
  - The tuple represents an inclusive line span: the symbol occupies every line
    from start through end inclusive
  - start is the "start" position's line, clamped to a minimum of 0
  - When the "end" position's character is non-zero, end is the "end" position's
    line (clamped to a minimum of start), reflecting that the half-open LSP range
    includes at least one character on that line
  - When the "end" position's character is 0 and the end line is strictly greater
    than start, end is one less than the "end" position's line, because a
    character of 0 means the symbol occupies no part of that final line

---

### Actual Behavior

The function returns a tuple (start, end) of two integers representing a 0-based inclusive line span. start is set to max(0, symbol_range['start']['line']). Let raw_end = max(start, symbol_range['end']['line']) (the end line from the input). If raw_end > start and the 'character' field of the 'end' dictionary is 0 (or missing, defaulting to 0), then end is set to raw_end - 1; otherwise end is raw_end. Formally, given the pre-condition that symbol_range['start'] and symbol_range['end'] each contain an integer 'line', let S = int(symbol_range['start']['line']), E_line = int(symbol_range['end']['line']), E_char = int(symbol_range['end'].get('character', 0)). Then the returned tuple (s, e) satisfies: s = max(0, S); e = (max(s, E_line) - 1) if max(s, E_line) > s and E_char == 0 else max(s, E_line).

---

## Code Evidence

Line 482 (real source: `src/languages/erlang.py`): `if end > start and int(end_position.get("character", 0)) == 0:`

---

## Trigger Condition

The specification distinguishes between zero and non-zero character. The code casts the character to int, which truncates non-integer values like 0.5 to 0. For the input above, start=0, end_line=2, character=0.5. The code sees int(0.5)==0, so it subtracts 1 from end, returning (0,1). The spec treats 0.5 as non-zero, so end should be 2 (the end line), returning (0,2). The cast breaks the intended behavior for non-integer non-zero character values.

---

## How to trigger the bug

Describe the concrete inputs used in the probe, what the buggy code returns, and what the specification requires.

### Inputs

| Parameter | Value |
|-----------|-------|
| `symbol_range["start"]["line"]` | `0` |
| `symbol_range["end"]["line"]` | `2` |
| `symbol_range["end"]["character"]` | `0.5` |

### Expected (spec-correct) Output

`(0, 2)` — character is non-zero (0.5), so end should be the raw end line (2).

### Actual (buggy) Output

`(0, 1)` — `int(0.5)` truncates to `0`, so the code erroneously subtracts 1 from end.

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
from src.languages.erlang import _symbol_line_span

result = _symbol_line_span({
    "start": {"line": 0},
    "end":   {"line": 2, "character": 0.5},
})
print(result)
# actual (buggy) output: (0, 1)
# expected (correct) output: (0, 2)
```

---

## Probe Script

```python
import sys
import os

# Add workspace root to path so `src` is importable
_workspace = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _workspace not in sys.path:
    sys.path.insert(0, _workspace)

try:
    from src.languages.erlang import _symbol_line_span

    # Trigger condition: character=0.5 (a non-zero float).
    # The code uses int(character) which truncates 0.5 to 0, so it
    # erroneously treats character as zero and subtracts 1 from end.
    # Spec says non-zero character → end should be the raw end line (no subtraction).
    symbol_range = {
        "start": {"line": 0},
        "end":   {"line": 2, "character": 0.5},
    }
    actual   = _symbol_line_span(symbol_range)
    expected = (0, 2)  # spec-correct: end=2 because character is non-zero
    passed   = actual != expected

    if passed:
        print(f"CONFIRMED — actual: {actual!r} | expected: {expected!r}")
    else:
        print(f"NOT CONFIRMED — actual matched expected: {actual!r}")

except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)
```

### Probe Output

```
CONFIRMED — actual: (0, 1) | expected: (0, 2)
```

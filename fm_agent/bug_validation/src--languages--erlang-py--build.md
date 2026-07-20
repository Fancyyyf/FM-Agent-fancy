# Bug Report: build

**Source file:** `/tmp/fm_agent_wt_FM-Agent_dlsr6ukl/snapshot/fm_agent/extracted_functions/src/languages/erlang-py/build.py`
**Verdict:** MISMATCH
**Confirmation status:** not_confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- Returns an instance of cls initialized from source
  - The returned instance supports mapping a
    (start_line, end_line) line-number pair to the substring
    of source spanning from the start line (inclusive) to
    the end line (exclusive)
  - The returned instance supports converting a
    (line, character) position to a 0-based byte offset
    within source
  - Line-break characters in source are preserved exactly as
    they appear in the input string

---

### Actual Behavior

After execution, the method returns an instance obj of cls, such that: obj.source == source, obj.lines == source.splitlines(keepends=True), and obj.line_offsets is a list with len(obj.line_offsets) == len(obj.lines) where obj.line_offsets[0] == 0 and for all i in range(1, len(obj.line_offsets)): obj.line_offsets[i] == obj.line_offsets[i-1] + len(obj.lines[i-1]).

---

## Code Evidence

Line 2: lines = source.splitlines(keepends=True)
Line 3: line_offsets = []

---

## Trigger Condition

When source is the empty string, splitlines returns an empty list, so line_offsets remains an empty list. The resulting instance cannot convert a (0, 0) position to a 0-based offset because line_offsets[0] would raise an IndexError, violating the specification's requirement to support position-to-offset conversion for valid positions.

---

## How to trigger the bug

The bug is structural but does not manifest behaviorally through the public API. While `build("")` does produce an instance with `line_offsets = []` (violating the implicit expectation that `line_offsets` should have at least one entry), the `position_to_offset` method has a guard (`if line_number >= len(self.lines): return len(self.source)`) that prevents the IndexError from actually occurring.

### Inputs

| Parameter | Value |
|-----------|-------|
| `source` | `""` (empty string) |
| `position` | `{"line": 0, "character": 0}` |

### Expected (spec-correct) Output

`0` (the 0-based byte offset of position (0,0) in an empty string)

### Actual (buggy) Output

`0` (the guard `if line_number >= len(self.lines)` returns `len(self.source)` which is `0`, avoiding the IndexError)

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import sys
import os
_workspace = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _workspace)

from src.languages.erlang import _position_to_offset

result = _position_to_offset("", {"line": 0, "character": 0})
# actual (buggy) output: 0
# expected (correct) output: 0
print(result)
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
    from src.languages.erlang import _position_to_offset, _source_for_range

    source = ""

    # Test empty source with position (0, 0)
    # Trigger: empty source → empty lines/line_offsets → guard check: line_number(0) >= len(lines)(0) → True → returns len(source)=0
    # If guard were absent, line_offsets[0] would raise IndexError
    try:
        actual = _position_to_offset(source, {"line": 0, "character": 0})
        expected = 0  # spec-correct: byte offset of position (0,0) in empty string is 0
        if actual != expected:
            print(f"CONFIRMED — _position_to_offset returned {actual!r}, expected {expected!r}")
        else:
            print(f"NOT CONFIRMED — _position_to_offset returned {actual!r} (matches expected)")
    except IndexError as e:
        print(f"CONFIRMED — IndexError in _position_to_offset: {e}")
    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)

except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)
```

### Probe Output

```
NOT CONFIRMED — _position_to_offset returned 0 (matches expected)
```

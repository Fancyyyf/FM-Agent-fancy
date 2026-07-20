# Bug Report: _split_spec_and_info

**Source file:** `/tmp/fm_agent_wt_FM-Agent__ro_f_c_/snapshot/fm_agent/extracted_functions/src/incremental_reasoner-py/_split_spec_and_info.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- Returns a 2-tuple (spec_block, info_block)
  - When block contains at least two spec-delimiter lines, spec_block is the substring
    from (and including) the first spec-delimiter line through (and including) the second
    spec-delimiter line, with leading and trailing blank lines removed
  - When block contains zero or one spec-delimiter lines but at least one info-delimiter
    line, spec_block is the substring from the start of block through the line immediately
    preceding the first info-delimiter line, with leading and trailing blank lines removed
  - When block contains neither two spec-delimiters nor any info-delimiter, spec_block is
    block itself with trailing newlines removed and info_block is None
  - info_block is the substring from (and including) the first info-delimiter line through
    (and including) the second info-delimiter line when two or more info-delimiter lines
    exist; when exactly one exists, info_block extends from that line to the end of block;
    in both cases leading and trailing blank lines are removed
  - When no info-delimiter line exists anywhere in block, info_block is None
  - The operation is a deterministic, pure text transformation: it performs no file I/O,
    no network calls, and no mutation of any external state

---

### Actual Behavior

The function returns a tuple (spec_block, info_block) with no side effects. Define lines = block.splitlines(), spec_tag = spec_marker.strip(), info_tag = (comment_prefix + ' [INFO]').strip(), spec_idxs = [i for i, ln in enumerate(lines) if ln.strip() == spec_tag], info_idxs = [i for i, ln in enumerate(lines) if ln.strip() == info_tag]. Then: (1) If len(spec_idxs) < 2 and len(info_idxs) == 0, return (block.strip('\n'), None). (2) Otherwise, set spec_end = spec_idxs[1] if len(spec_idxs) >= 2 else info_idxs[0] - 1; spec_block = '\n'.join(lines[:spec_end+1]).strip('\n'). (3) If len(info_idxs) >= 2, info_block = '\n'.join(lines[info_idxs[0]:info_idxs[1]+1]).strip('\n'). Else if len(info_idxs) == 1, info_block = '\n'.join(lines[info_idxs[0]:]).strip('\n'). Else info_block = None. (4) Return (spec_block, info_block).

---

## Code Evidence

Line 17: spec_end = spec_idxs[1] and Line 22: spec_block = '\n'.join(lines[: spec_end + 1]).strip('\n')

---

## Trigger Condition

When block contains two spec delimiters, the code incorrectly includes all lines from the start of block up to the second spec delimiter, instead of starting from the first spec delimiter as required by the specification. For the given counterexample, the code returns spec_block='extra\n[SPEC]\ncontent\n[SPEC]' but the specification requires '[SPEC]\ncontent\n[SPEC]'.

---

## How to trigger the bug

Describe the concrete inputs used in the probe, what the buggy code returns, and what the specification requires.

### Inputs

| Parameter | Value |
|-----------|-------|
| block | `"extra\n[SPEC]\ncontent\n[SPEC]"` |
| comment_prefix | `"#"` |
| spec_marker | `"[SPEC]"` |

### Expected (spec-correct) Output

`"[SPEC]\ncontent\n[SPEC]"`

### Actual (buggy) Output

`"extra\n[SPEC]\ncontent\n[SPEC]"`

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
from src.incremental_reasoner import _split_spec_and_info

block = "extra\n[SPEC]\ncontent\n[SPEC]"
spec_block, info_block = _split_spec_and_info(block, "#", "[SPEC]")
# actual (buggy) output: "extra\n[SPEC]\ncontent\n[SPEC]"
# expected (correct) output: "[SPEC]\ncontent\n[SPEC]"
# root cause: line 531 uses lines[: spec_end + 1] instead of lines[spec_idxs[0] : spec_end + 1]
```

---

## Probe Script

```python
import sys
sys.path.insert(0, '.')

try:
    from src.incremental_reasoner import _split_spec_and_info
except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)

# Trigger condition: block with text before the first [SPEC] delimiter and two [SPEC] delimiters
# The spec requires spec_block from (and including) the first spec-delimiter line
# through (and including) the second. The buggy code instead uses lines[:spec_end+1],
# incorrectly including all lines from the start of block up to the second delimiter.
block = "extra\n[SPEC]\ncontent\n[SPEC]"
comment_prefix = "#"
spec_marker = "[SPEC]"

try:
    actual_spec, actual_info = _split_spec_and_info(block, comment_prefix, spec_marker)

    # Per spec: spec_block should be from first [SPEC] through second [SPEC] (inclusive),
    # with leading and trailing blank lines removed.
    expected_spec = "[SPEC]\ncontent\n[SPEC]"
    expected_info = None

    # Bug confirmed if actual_spec != expected_spec
    passed = actual_spec != expected_spec

except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)

if passed:
    print(f'CONFIRMED — actual: {actual_spec!r} | expected: {expected_spec!r}')
else:
    print(f'NOT CONFIRMED — actual matched expected: {actual_spec!r}')
```

### Probe Output

```
CONFIRMED — actual: 'extra\n[SPEC]\ncontent\n[SPEC]' | expected: '[SPEC]\ncontent\n[SPEC]'
```

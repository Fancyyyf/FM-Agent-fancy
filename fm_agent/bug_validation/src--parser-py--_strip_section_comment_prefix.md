# Bug Report: _strip_section_comment_prefix

**Source file:** `/tmp/fm_agent_wt_FM-Agent_dlsr6ukl/snapshot/fm_agent/extracted_functions/src/parser-py/_strip_section_comment_prefix.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- Returns a string where any leading comment prefix at the start of the line
    (after optional leading whitespace) has been removed
  - A recognized comment prefix consists of one or more consecutive characters
    from the set {`/`, `#`, `-`, `%`}, all of the same character, optionally
    followed by a single whitespace character
  - Leading whitespace characters that precede the comment prefix are preserved
    unchanged in the returned string
  - When the line does not begin with (optional leading whitespace followed by)
    a recognized comment prefix, the line is returned unchanged

---

### Actual Behavior

Returns a string equal to `re.sub(r'^(\s*)(?://+|#+|--+|%+)\s?', r'\1', line)`. Specifically, if `line` starts with any amount of whitespace followed by one or more comment characters from the set `//`, `#`, `--`, `%` and optionally a single whitespace character, then the matched comment prefix and optional whitespace are removed, leaving only the leading whitespace; otherwise the original `line` is returned unchanged.

---

## Code Evidence

Line 2:     return re.sub(r'^(\s*)(?://+|#+|--+|%+)\s?', r'\1', line)

---

## Trigger Condition

The code requires at least two '/' or '-' characters to recognize a comment prefix, but the specification allows a single '/' or '-'. Input ' / comment' contains a single '/' after leading whitespace, which should be removed per spec but is not removed by the code.

---

## How to trigger the bug

Describe the concrete inputs used in the probe, what the buggy code returns, and what the specification requires.

### Inputs

| Parameter | Value |
|-----------|-------|
| `line` | `" / comment"` |
| `line` | `" - comment"` |

### Expected (spec-correct) Output

`" comment"` (for `" / comment"` — leading whitespace preserved, single `/` + trailing space removed)
`" comment"` (for `" - comment"` — leading whitespace preserved, single `-` + trailing space removed)

### Actual (buggy) Output

`" / comment"` (unchanged — `//+` requires at least two `/` characters)
`" - comment"` (unchanged — `--+` requires at least two `-` characters)

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import sys, re
sys.path.insert(0, '.')
from src.parser import _strip_section_comment_prefix

line = " / comment"
actual = _strip_section_comment_prefix(line)
# actual (buggy) output: " / comment"
# expected (correct) output: " comment"
```

---

## Probe Script

```python
import sys
import re
sys.path.insert(0, '.')

try:
    from src.parser import _strip_section_comment_prefix
except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)

# Correct regex per spec: one or more of each comment char (not two+ for / and -)
_correct_re = re.compile(r'^(\s*)(?:/+|#+|-+|%+)\s?')

tests = [
    (" / comment", " / comment"),
    (" - comment", " - comment"),
]

any_confirmed = False
for line, label in tests:
    actual = _strip_section_comment_prefix(line)
    expected = _correct_re.sub(r'\1', line)

    if actual != expected:
        any_confirmed = True
        print(f'CONFIRMED ({label}): actual={actual!r} | expected={expected!r}')
    else:
        print(f'NOT CONFIRMED ({label}): actual matched expected: {actual!r}')

if not any_confirmed:
    print('NOT CONFIRMED — all inputs matched expected output')
```

### Probe Output

```
CONFIRMED ( / comment): actual=' / comment' | expected=' comment'
CONFIRMED ( - comment): actual=' - comment' | expected=' comment'
```

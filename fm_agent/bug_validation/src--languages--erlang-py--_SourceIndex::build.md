# Bug Report: _SourceIndex::build

**Source file:** `/tmp/fm_agent_wt_FM-Agent_xyeqtgt6/snapshot/fm_agent/extracted_functions/src/languages/erlang-py/_SourceIndex::build.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- Returns a _SourceIndex instance whose content is derived solely from source
  - The returned index represents source as an ordered sequence of lines,
    where line boundaries correspond to newline character positions in source
  - For each line, the byte offset of its first character within source is
    computable from the returned index
  - The total number of bytes across all lines in the returned index equals
    the length of source

---

### Actual Behavior

The method returns an instance of `cls` (expected to be `_SourceIndex` or a subclass) with three attributes: `source` equals the original input string `source`, `lines` is the list of strings obtained by calling `source.splitlines(keepends=True)`, and `line_offsets` is a list of integers where each element represents the character offset of the start of the corresponding line in the original source. Formally, let `r` be the returned object. Then r.source == source, r.lines == source.splitlines(keepends=True), len(r.line_offsets) == len(r.lines), and for all i, 0  i < len(r.lines), r.line_offsets[i] == _{j=0}^{i-1} len(r.lines[j]) (with the sum defined as 0 when i=0). No exceptions are raised and no other side effects occur.

---

## Code Evidence

Line 2: lines = source.splitlines(keepends=True)

---

## Trigger Condition

The specification requires line boundaries to correspond only to newline character positions. For source='hello\vworld', the vertical tab (\v) is not a standard newline character, but splitlines(keepends=True) splits on it, creating two lines ('hello\v' and 'world') and computing line offsets accordingly. This violates the requirement that the returned index represents source as an ordered sequence of lines where line boundaries correspond to newline positions.

---

## How to trigger the bug

The bug manifests when the source string contains Unicode line break characters that are not standard newlines (`\n`, `\r`, `\r\n`). Python's `str.splitlines(keepends=True)` splits on a wider set of characters defined as line boundaries by the Unicode standard, including vertical tab (`\v` / `\x0b`), form feed (`\f`), next line (`\x85`), line separator (`\u2028`), and paragraph separator (`\u2029`).

### Inputs

| Parameter | Value |
|-----------|-------|
| `source` | `'hello\vworld'` |

### Expected (spec-correct) Output

A `_SourceIndex` with `lines = ['hello\vworld']` (1 line — `\v` is not a newline character)

### Actual (buggy) Output

A `_SourceIndex` with `lines = ['hello\v', 'world']` (2 lines — `splitlines(keepends=True)` incorrectly treats `\v` as a line boundary)

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import sys
sys.path.insert(0, '.')
from src.languages.erlang import _SourceIndex

source = 'hello\vworld'
idx = _SourceIndex.build(source)
print(idx.lines)
# actual (buggy) output: ['hello\x0b', 'world']  (2 lines)
# expected (correct) output: ['hello\x0bworld']   (1 line)
```

---

## Probe Script

```python
import sys
try:
    from src.languages.erlang import _SourceIndex

    # Trigger condition: source contains a vertical tab (\v) which is NOT a newline
    # The specification requires line boundaries correspond only to newline chars,
    # but splitlines(keepends=True) also splits on \v, \f, \x85, etc.
    source = 'hello\vworld'
    idx = _SourceIndex.build(source)

    # Spec-correct: \v is not a newline → source should be 1 line
    # Buggy actual: splitlines(keepends=True) splits on \v → 2 lines
    expected_lines = 1  # 'hello\vworld' is a single line with no newline
    actual_lines = len(idx.lines)

    passed = actual_lines != expected_lines

    if passed:
        print(f'CONFIRMED — actual lines: {actual_lines!r} | expected lines: {expected_lines!r}')
        print(f'lines: {idx.lines!r}')
        print(f'line_offsets: {idx.line_offsets!r}')
        print(f'source: {source!r}')
    else:
        print(f'NOT CONFIRMED — actual matched expected: {actual_lines} lines')
        print(f'lines: {idx.lines!r}')
except Exception as e:
    print(f'ERROR: {e}')
    import traceback
    traceback.print_exc()
    sys.exit(1)
```

### Probe Output

```
CONFIRMED — actual lines: 2 | expected lines: 1
lines: ['hello\x0b', 'world']
line_offsets: [0, 6]
source: 'hello\x0bworld'
```

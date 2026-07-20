# Bug Report: is_file_ready

**Source file:** `src/file_utils.py`
**Verdict:** MISMATCH
**Confirmation status:** not_confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- Returns True if and only if all of the following hold:
    1. The file at file_path exists, can be opened, and can be decoded as UTF-8 text
       (with optional BOM-stripping).
    2. The file content begins with a [SPEC] section consisting of an opening marker line
       and a closing marker line, followed by an [INFO] section consisting of an opening
       marker line and a closing marker line.
    3. Every marker line matches the pattern of a language-appropriate single-line comment
       prefix (one or more repetitions of the comment-start character) followed immediately
       by the bracketed section label [SPEC] or [INFO].
    4. All four marker lines share the same comment prefix.
    5. Every non-empty line appearing after the first SPEC marker and before the final
       INFO marker is either one of the four required marker lines or begins with the same
       comment prefix as those marker lines.
    6. No line matching the marker pattern (comment prefix followed by [SPEC] or [INFO])
       appears out of the required SPEC → SPEC → INFO → INFO order before the fourth
       marker is reached.
  - Returns False if the file does not exist, cannot be opened, cannot be decoded as
    UTF-8, fails to contain all four markers in the required order, has inconsistent
    comment prefixes, or contains non-comment content between the markers.

---

### Actual Behavior

After execution, the function returns a Boolean value, denoted `result`, with the following properties: (1) If any exception of type OSError or UnicodeDecodeError occurs during opening or reading the file at `file_path`, then `result` is `False` and no exception propagates. (2) Otherwise, let `content` be the file's entire text decoded using 'utf-8-sig', and let `S` be the list `_READY_SECTION_ORDER`. Let `lines` be the sequence of strings obtained by splitting `content` at line boundaries. Then `result` is `True` if and only if there exists a prefix `prefix` (a string) and an index `i` into `lines` such that: (a) All lines before `i` are blank (contain only whitespace) and may be empty; (b) The line `lines[i]` fully matches the regular expression `_READY_MARKER_RE` and its named group `section` equals `S[0]`; (c) Let `prefix` be the value of the named group `prefix` from that match; (d) For all subsequent lines starting from `i+1`, the following invariants hold while processing: (i) If a line `L` fully matches `_READY_MARKER_RE` with group `section` equal to the next expected element of `S` (in order) and group `prefix` equal to `prefix`, then that section is consumed; if after consuming the last element of `S`, the function immediately returns `True` without requiring any further lines. (ii) Any line that does not match the marker must, if it is non-blank (stripped length > 0), have its leading non-whitespace portion start with `prefix`; blank lines are allowed and ignored. (iii) If a marker's `section` does not match the expected one, or its `prefix` differs from the established `prefix`, or a non-blank non-marker line does not start with `prefix`, the condition is violated and `result` becomes `False`. (iv) If all lines are exhausted before all elements of `S` have been matched in order, `result` is `False`. (3) In all cases, the file is properly closed after reading, and the global state (other than file system side-effects of opening/closing the file) remains unmodified.

---

## Code Evidence

Line 14: marker = _READY_MARKER_RE.fullmatch(line) fails to match due to leading whitespace; Line 16: returns False because marker is None and before_header is True

---

## Trigger Condition

The specification does not forbid leading whitespace on marker lines, as a line containing a comment prefix followed immediately by the section label still matches the described pattern. The code's use of fullmatch requires the whole line to exactly match the marker regex without any leading whitespace, causing it to incorrectly reject a file that should be valid according to the specification.

---

## How to trigger the bug

### Inputs

| Parameter | Value |
|-----------|-------|
| file_path | path to a Python file whose [SPEC]/[INFO] marker lines have leading whitespace (e.g., `  # [SPEC]` instead of `# [SPEC]`) |

### Expected (spec-correct) Output

`True` — the specification does not forbid leading whitespace on marker lines, so a file with properly ordered markers and consistent prefixes should be accepted even if the markers are indented.

### Actual (buggy) Output

`True` — after empirical testing, `is_file_ready` returns `True` for a file with leading whitespace on all marker lines. The regex `_READY_MARKER_RE` is `r"^\s*(?P<prefix>//+|#+|--+|%+)\s*\[(?P<section>SPEC|INFO)\]\s*$"`, which includes `^\s*` and therefore explicitly permits leading whitespace. The claimed bug does not reproduce.

### How to Reproduce

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
from src.file_utils import is_file_ready
import tempfile, os

content = """  # [SPEC]
  # unit: test
  # [SPEC]

  # [INFO]
  # (no callees)
  # [INFO]
"""
with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
    f.write(content)
    path = f.name

result = is_file_ready(path)
os.unlink(path)
# actual (buggy) output: True
# expected (correct) output: True — the bug is NOT confirmed; behavior matches spec
```

---

## Probe Script

```python
import sys
import os
import tempfile

try:
    from src.file_utils import is_file_ready
except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)

test_content = """  # [SPEC]
  # Unit: test.py
  #
  # Test function
  # [SPEC]

  # [INFO]
  # (no callees)
  # [INFO]
"""

with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
    f.write(test_content)
    tmp_path = f.name

try:
    actual = is_file_ready(tmp_path)
    expected = True
    passed = actual != expected
except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)
finally:
    os.unlink(tmp_path)

if passed:
    print(f'CONFIRMED — actual: {actual!r} | expected: {expected!r}')
else:
    print(f'NOT CONFIRMED — actual matched expected: {actual!r}')
```

### Probe Output

```
NOT CONFIRMED — actual matched expected: True
```

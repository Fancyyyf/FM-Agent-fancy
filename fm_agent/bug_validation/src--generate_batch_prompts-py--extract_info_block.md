# Bug Report: extract_info_block

**Source file:** `src/generate_batch_prompts.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- If the file content contains two or more lines matching "<prefix> [INFO]"
    where <prefix> is the single-line comment marker of the source language
    ("#", "//", or "%"), returns the text between the first such line and the
    second such line, exclusive of both marker lines, with leading and trailing
    whitespace removed
  - Returns None when the file content contains no recognized comment prefix, or
    contains fewer than two "<prefix> [INFO]" marker lines
  - File open/read errors (e.g., file not found, permission denied) propagate to
    the caller; Unicode decoding errors are replaced with the replacement character

---

### Actual Behavior

The function result satisfies: Let C = filepath.read_text(errors="replace") (no exceptions due to valid pre-condition). Let p = _detect_comment_prefix(C). If p is None, result is None. Else let tag = p + " [INFO]". Let i = C.find(tag). If i == -1, result is None. Else let j = C.find(tag, i + len(tag)). If j == -1, result is None. Else result = C[i + len(tag) + 1 : j].strip(). The function has no side effects on the file or its content.

---

## Code Evidence

Line 8: start = content.find(tag)

---

## Trigger Condition

The code locates the marker substring anywhere in the content instead of requiring it to appear as a whole line matching '<prefix> [INFO]'. This causes the first marker to match inside a non-marker line, selecting wrong boundaries and returning incorrect text (empty string instead of 'some text') against the specification.

---

## How to trigger the bug

The bug is triggered when the `<prefix> [INFO]` tag appears as a substring within a non-marker line (e.g., mentioned in prose within a comment) before the first actual whole-line marker. `str.find()` picks the mid-line occurrence as `start`, causing the returned text to be the fragment between that mid-line position and the next marker, rather than the content between the two proper whole-line markers.

### Inputs

| Parameter | Value |
|-----------|-------|
| filepath | Path to a file containing a mid-line `# [INFO]` mention before the actual markers |

### Expected (spec-correct) Output

`actual info content`

### Actual (buggy) Output

`here`

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import tempfile
from pathlib import Path
from src.generate_batch_prompts import extract_info_block

test_content = (
    "# [SPEC]\n"
    "# Unit: test_file.py\n"
    "# [SPEC]\n"
    "\n"
    "# Some text that mentions # [INFO] here\n"
    "# [INFO]\n"
    "actual info content\n"
    "# [INFO]\n"
)

with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as tf:
    tf.write(test_content)
    tmp_path = Path(tf.name)

result = extract_info_block(tmp_path)
print(result)
# actual (buggy) output: 'here'
# expected (correct) output: 'actual info content'
```

---

## Probe Script

```python
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, ".")

try:
    from src.generate_batch_prompts import extract_info_block
except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)

# Trigger condition: The buggy code uses content.find(tag) which matches the
# "# [INFO]" marker as a substring anywhere in the file. Per the spec, the
# marker must appear as a whole line. When "# [INFO]" appears mid-line before
# the first whole-line marker, c.find() picks the mid-line occurrence, causing
# wrong boundary selection.

test_content = (
    "# [SPEC]\n"
    "# Unit: test_file.py\n"
    "# [SPEC]\n"
    "\n"
    "# Some text that mentions # [INFO] here\n"
    "# [INFO]\n"
    "actual info content\n"
    "# [INFO]\n"
)

with tempfile.NamedTemporaryFile(
    mode="w", suffix=".py", delete=False, encoding="utf-8"
) as tf:
    tf.write(test_content)
    tmp_path = Path(tf.name)

try:
    actual = extract_info_block(tmp_path)
    # Spec: text between first whole-line # [INFO] and second whole-line # [INFO]
    # That's between line 7 and line 9 → "actual info content"
    expected = "actual info content"
    passed = actual != expected
except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)
finally:
    tmp_path.unlink(missing_ok=True)

if passed:
    print(f"CONFIRMED — actual: {actual!r} | expected: {expected!r}")
else:
    print(f"NOT CONFIRMED — actual matched expected: {actual!r}")
```

### Probe Output

```
CONFIRMED — actual: 'here' | expected: 'actual info content'
```

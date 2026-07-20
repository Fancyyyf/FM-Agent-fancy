# Bug Report: extract_spec_block

**Source file:** `src/generate_batch_prompts-py/extract_spec_block.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- If the file content begins with the line "<prefix> [SPEC]" where <prefix>
    is the single-line comment marker of the source language ("#", "//", or "%")
    and contains a second "<prefix> [SPEC]" line after the first, returns the
    complete text from the start of the file through the closing "<prefix> [SPEC]"
    line inclusive, with surrounding whitespace stripped
  - Returns None when the file content contains no recognized comment prefix, or
    does not begin with a "<prefix> [SPEC]" line, or contains only one such line
  - File open/read errors (e.g., file not found, permission denied) propagate to
    the caller; Unicode decoding errors are replaced with the replacement character

---

### Actual Behavior

The function returns a non-None string if and only if the file content meets all of the following conditions: (1) _detect_comment_prefix(content) returns a non-None prefix p (i.e., the content contains at least one of the single-line comment starters '#', '//', or '%'); (2) the content begins with the string p + ' [SPEC]' (3) the content contains at least two occurrences of that tag, with the second occurrence starting at an index >= len(tag) (i.e., content.find(p + ' [SPEC]', len(p + ' [SPEC]')) != -1). When all conditions hold, the returned value is content[0:end+len(tag)].strip(), where tag = p + ' [SPEC]' and end = content.find(tag, len(tag)). If any condition fails, the function returns None. No file-related exception is raised because the file is known to exist, be readable, and read_text uses errors='replace'. Formally: let content = filepath.read_text(errors='replace'); let p = _detect_comment_prefix(content) in (if p = None then return None else (let tag = p + ' [SPEC]' in (if not content.startswith(tag) then return None else (let end = content.find(tag, len(tag)) in (if end = -1 then return None else return strip(content[0 : end+len(tag)])))))

---

## Code Evidence

Line 8: if not content.startswith(tag):
Line 10: end = content.find(tag, len(tag))

---

## Trigger Condition

The specification requires the file to begin with the line '<prefix> [SPEC]', i.e., the first line must be exactly that tag (possibly followed by a newline or end-of-file). The code checks only content.startswith(tag), so it accepts content that starts with the tag but does not form a complete line (e.g., '// [SPEC]extra'). Additionally, the code uses find(tag, len(tag)) to locate a second occurrence anywhere, whereas the specification demands a second '<prefix> [SPEC]' line. Therefore, a file whose first line is '// [SPEC]extra' followed by a second line '// [SPEC]' is wrongly accepted and returns a non-None string instead of None.

---

## How to trigger the bug

A file whose first line starts with the `<prefix> [SPEC]` tag but has extra characters (e.g., `// [SPEC]extra`) followed by a valid closing `<prefix> [SPEC]` line is wrongly accepted as a spec block. The specification requires the first line to be **exactly** the tag, not just start with it.

### Inputs

| Parameter | Value |
|-----------|-------|
| filepath | Temp file with content: `// [SPEC]extra junk on first line\n\nsome arbitrary code here\n\n// [SPEC]\n` |

### Expected (spec-correct) Output

`None`

### Actual (buggy) Output

`'// [SPEC]extra junk on first line\n\nsome arbitrary code here\n\n// [SPEC]'`

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import tempfile
from pathlib import Path
from src.generate_batch_prompts import extract_spec_block

test_content = (
    "// [SPEC]extra junk on first line\n"
    "\n"
    "some arbitrary code here\n"
    "\n"
    "// [SPEC]\n"
)
with tempfile.NamedTemporaryFile(mode="w", suffix=".c", delete=False, encoding="utf-8") as tf:
    tf.write(test_content)
    tmp_path = Path(tf.name)

result = extract_spec_block(tmp_path)
print(repr(result))
tmp_path.unlink()
# actual (buggy) output: '// [SPEC]extra junk on first line\n\nsome arbitrary code here\n\n// [SPEC]'
# expected (correct) output: None
```

---

## Probe Script

```python
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, ".")

try:
    from src.generate_batch_prompts import extract_spec_block
except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)

# Trigger condition: The specification requires the file to begin with the
# LINE "<prefix> [SPEC]" — the first line must be exactly that tag, not just
# start with it. The code checks only content.startswith(tag), so it accepts
# content whose first line is "// [SPEC]extra" as a valid spec block start,
# when it should return None.
#
# This test file's first line is "// [SPEC]extra" (not a valid spec start line)
# followed by a closing "// [SPEC]" line. Per spec, this should return None.
# The buggy code returns a non-None block because startswith matches.

test_content = (
    "// [SPEC]extra junk on first line\n"
    "\n"
    "some arbitrary code here\n"
    "\n"
    "// [SPEC]\n"
    "# trailing content\n"
)

with tempfile.NamedTemporaryFile(
    mode="w", suffix=".c", delete=False, encoding="utf-8"
) as tf:
    tf.write(test_content)
    tmp_path = Path(tf.name)

try:
    actual = extract_spec_block(tmp_path)
    # Per spec: file does not begin with a "<prefix> [SPEC]" LINE, so should return None.
    expected = None
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
CONFIRMED — actual: '// [SPEC]extra junk on first line\n\nsome arbitrary code here\n\n// [SPEC]' | expected: None
```

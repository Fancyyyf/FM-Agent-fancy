# Bug Report: _detect_comment_prefix

**Source file:** `src/generate_batch_prompts-py/_detect_comment_prefix.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- If content contains at least one line in which the substring "[SPEC]" appears,
    returns the text preceding "[SPEC]" on the first such line (by ascending line
    order), with trailing whitespace removed from that prefix text
  - Otherwise, returns None
  - The returned value, when not None, is the single-line comment prefix used in
    the source file ("#" for Python, "//" for C-family languages, "%" for Erlang)

---

### Actual Behavior

The function returns the string obtained from the first line of `content` that contains the substring '[SPEC]', by extracting the part before '[SPEC]' and removing trailing whitespace, or `None` if no line contains '[SPEC]'. Formally: Let `lines = content.splitlines()`. If there exists an index `i` such that `lines[i].find('[SPEC]') != -1`, let `first = lines[i]` and `idx = first.find('[SPEC]')`; the function returns `first[:idx].rstrip()`. Otherwise, the function returns `None`.

---

## Code Evidence

Line 6: return line[:idx].rstrip()

---

## Trigger Condition

The code returns "hello", which is not a valid single-line comment prefix (e.g., '#', '//', '%'), violating the specification that the returned value must be a comment prefix.

---

## How to trigger the bug

When the input content contains a line where `[SPEC]` is preceded by arbitrary text that is not a valid comment prefix (like `#`, `//`, `%`, `--`), `_detect_comment_prefix` returns that arbitrary text as the "comment prefix" without any validation. The specification states the returned value **is** a valid single-line comment prefix, but the function blindly returns whatever text appears before `[SPEC]`.

### Inputs

| Parameter | Value |
|-----------|-------|
| content | `"hello [SPEC]\n# Unit: test\nhello [SPEC]\n"` |

### Expected (spec-correct) Output

`None` (no valid comment prefix found; `"hello"` is not `#`, `//`, `%`, or `--`)

### Actual (buggy) Output

`"hello"` (the function extracts `"hello"` before `[SPEC]` without checking if it's a real comment prefix)

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import sys
sys.path.insert(0, ".")

from src.generate_batch_prompts import _detect_comment_prefix

content = "hello [SPEC]\n# Unit: test\nhello [SPEC]\n"
result = _detect_comment_prefix(content)
print(repr(result))
# actual (buggy) output: 'hello'
# expected (correct) output: None
```

---

## Probe Script

```python
import sys
import os

# Ensure repo root is in sys.path for package import
repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

try:
    from src.generate_batch_prompts import _detect_comment_prefix
except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)

# Valid comment prefixes from the spec
VALID_PREFIXES = {'#', '//', '%', '--'}

# Trigger: content where [SPEC] is preceded by "hello" — NOT a valid comment prefix
content = "hello [SPEC]\n# Unit: test\nhello [SPEC]\n"

try:
    result = _detect_comment_prefix(content)
except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)

# Per spec, the returned value should be a valid comment prefix (or None if none found).
# The bug: _detect_comment_prefix returns "hello" (not a valid prefix) without validation.
expected = None  # Per spec, non-comment text before [SPEC] should not be treated as a prefix
actual = result

# Bug is CONFIRMED if: result is non-None AND result is NOT a valid comment prefix
bug_confirmed = result is not None and result not in VALID_PREFIXES

if bug_confirmed:
    print(f'CONFIRMED — actual: {actual!r} | expected valid prefix or None; '
          f'_detect_comment_prefix returned invalid comment prefix "{actual}"')
else:
    print(f'NOT CONFIRMED — actual: {actual!r} | expected: {expected!r}')
```

### Probe Output

```
CONFIRMED — actual: 'hello' | expected valid prefix or None; _detect_comment_prefix returned invalid comment prefix "hello"
```

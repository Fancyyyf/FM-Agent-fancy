# Bug Report: _generic_func_info

**Source file:** `src/scope.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- Returns a dict containing the canonical metadata and signal fields
    for one function extracted from a generic (non-Python) source file
  - The returned dict has exactly the following keys, all present:
    * 'name': str — equal to the input name parameter
    * 'start': int — equals start0 + 1 (1-based inclusive start line)
    * 'end': int — equals end0 + 1 (1-based inclusive end line)
    * 'calls': set[str] — names of functions called within the body,
      case-preserved, excluding names present in lang_cfg['keywords']
    * 'idents': set[str] — lowercased identifier-like tokens extracted
      from the body
    * 'body_words': set[str] — lowercased alphabetic words of length
      ≥ 4 from the body, excluding common stop words
    * 'exc_types': set[str] — lowercased exception-type names extracted
      from the body
    * 'docstring': str — always the empty string ''
  - All token-extraction fields are scoped exclusively to the
    concatenation of source_lines[start0] through source_lines[end0]
    (inclusive)
  - Each set-valued field is empty when no tokens of that category are
    found in the body
  - The returned dict is deterministic for a given input

---

### Actual Behavior

The regex `[a-zA-Z]` used in the `body_words` extraction only matches ASCII letters (a-z, A-Z). Non-ASCII alphabetic characters such as `é`, `ñ`, `ü`, `ß`, `ø`, and accented/Cyrillic/Greek letters are excluded. The spec requires extracting all lowercased alphabetic words of length ≥ 4, but words containing any non-ASCII letter are silently dropped.

---

## Code Evidence

Line 617: `body_words = {w for w in re.findall(r'\b([a-zA-Z]{4,})\b', body_text.lower())
                  if w not in _STOP}`

---

## Trigger Condition

The specification requires extracting all lowercased alphabetic words of length ≥ 4. The code's regex `[a-zA-Z]` matches only ASCII letters, missing words with non-ASCII letters like 'café'. Thus body_words would be {'word'} instead of {'word', 'café'}.

---

## How to trigger the bug

Describe the concrete inputs used in the probe, what the buggy code returns, and what the specification requires.

### Inputs

| Parameter | Value |
|-----------|-------|
| name | `"test_func"` |
| start0 | `0` |
| end0 | `0` |
| source_lines | `["// function body with word and café"]` |
| lang_cfg | `{"keywords": {"if", "else", "for", "while", "return"}}` |

### Expected (spec-correct) Output

`body_words = {'café', 'word'}` (both "café" and "word" are lowercased alphabetic words of length ≥ 4)

### Actual (buggy) Output

`body_words = {'body', 'word'}` (only the ASCII-4-letter words "body" and "word" are captured; "café" is missed because `é` is not matched by `[a-zA-Z]`)

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
from src.scope import _generic_func_info

source_lines = ["// function body with word and café"]
result = _generic_func_info("test_func", 0, 0, source_lines, {"keywords": set()})
print(result["body_words"])
# actual (buggy) output: {'body', 'word'}
# expected (correct) output: {'café', 'word'}
```

---

## Probe Script

```python
"""Probe script for bug: _generic_func_info body_words regex misses non-ASCII alphabetic chars."""
import sys

try:
    from src.scope import _generic_func_info

    source_lines = ["// function body with word and café"]
    name = "test_func"
    lang_cfg = {"keywords": {"if", "else", "for", "while", "return"}}

    result = _generic_func_info(name, start0=0, end0=0, source_lines=source_lines, lang_cfg=lang_cfg)

    body_words = result["body_words"]

    expected = {"word", "café"}
    actual = body_words

    passed = actual != expected

except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)

if passed:
    print(f"CONFIRMED — actual: {sorted(actual)} | expected: {sorted(expected)}")
else:
    print(f"NOT CONFIRMED — actual matched expected: {sorted(actual)}")
```

### Probe Output

```
CONFIRMED — actual: ['body', 'word'] | expected: ['café', 'word']
```

# Bug Report: _score_class

**Source file:** `/home/fancy/Projects_Vault/FM-Agent/fm_agent/extracted_functions/src/scope-py/_score_class.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

Returns a non-negative float. The score is the sum of the following weighted components: (a) for each token in the class name's constituent parts that matches a token in signals['backtick_idents'], a fixed backtick-name overlap weight; (b) for each token in the class name's constituent parts that matches a token in signals['plain_idents'], a fixed class-name overlap weight; (c) for each token in the class name's constituent parts that matches a token in signals['all_words'], the same fixed class-name overlap weight; (d) for each token in the class name's constituent parts that matches a token in signals['dotted_classes'], a fixed dotted-reference overlap weight; (e) when cls['docstring'] is non-empty and truthy: for each alphabetic word of four or more characters in the docstring that is not a stop word and matches a token in signals['all_words'], a fixed class-doc overlap weight. When cls['docstring'] is empty or falsy, component (e) contributes zero. The returned value is exactly zero when no name-part token and no qualifying docstring-word token overlaps any of the specified signal sets.

---

### Actual Behavior

The function returns a non-negative float score computed as: let name = cls['name']; doc = cls['docstring']; name_parts = _name_parts(name). score = |name_parts  signals['backtick_idents']| * W_BACKTICK_NAME + |name_parts  signals['plain_idents']| * W_CLASS_NAME_MATCH + |name_parts  signals['all_words']| * W_CLASS_NAME_MATCH + |name_parts  signals['dotted_classes']| * W_DOTTED_REF + ( if doc  '' then |{w | w  re.findall(r'\b([a-zA-Z]{4,})\b', doc.lower())  w  _STOP}  signals['all_words']| * W_CLASS_DOC_MATCH else 0 ). The inputs cls and signals are not modified; no exceptions are raised.

---

## Code Evidence

Line 15: re.findall(r'\b([a-zA-Z]{4,})\b', cls['docstring'].lower())

---

## Trigger Condition

The regex restricts word extraction to ASCII letters [a-zA-Z], but the specification requires extraction of all alphabetic words (including non-ASCII letters). For docstring 'nave', the code finds no matching words and scores 0, while the specification would score W_CLASS_DOC_MATCH because 'nave' is an alphabetic word of five characters and appears in signals['all_words'].

---

## How to trigger the bug

The `_score_class` function uses `re.findall(r'\b([a-zA-Z]{4,})\b', cls['docstring'].lower())` to extract words from a class docstring for scoring against `signals['all_words']`. The character class `[a-zA-Z]` only matches ASCII letters, so any alphabetic word containing a non-ASCII character (e.g., `señor`, `naïve`, `café`, `über`) will not be extracted — even if it appears in `signals['all_words']`. The specification requires extraction of **all** alphabetic words, including those with non-ASCII letters.

### Inputs

| Parameter | Value |
|-----------|-------|
| `cls['name']` | `'TestClass'` |
| `cls['docstring']` | `'Contains the word señor in prose.'` |
| `signals['backtick_idents']` | `set()` |
| `signals['plain_idents']` | `set()` |
| `signals['all_words']` | `{'señor'}` |
| `signals['dotted_classes']` | `set()` |

### Expected (spec-correct) Output

`2.0` — the word `señor` (5 alphabetic characters, not a stop word) matches `signals['all_words']`, contributing `W_CLASS_DOC_MATCH` (2.0).

### Actual (buggy) Output

`0.0` — the regex `[a-zA-Z]{4,}` does not match `señor` because the character `ñ` is not in `[a-zA-Z]`. No docstring words are extracted, so `len(doc_words & signals['all_words'])` is 0.

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
from src.scope import _score_class

cls = {'name': 'TestClass', 'docstring': 'Contains the word señor in prose.'}
signals = {
    'backtick_idents': set(),
    'plain_idents': set(),
    'all_words': {'señor'},
    'dotted_classes': set(),
}
print(_score_class(cls, signals))
# actual (buggy) output: 0.0
# expected (correct) output: 2.0
```

---

## Probe Script

```python
"""Probe script for bug src--scope-py--_score_class.

Tests whether _score_class correctly matches non-ASCII alphabetic
words in docstrings against signals['all_words'].
"""

import sys
import tempfile
import os

# ── Use a fresh temp dir for probe workspace ──
original_cwd = os.getcwd()
tmpdir = tempfile.mkdtemp(prefix='probe_score_class_')
os.chdir(tmpdir)

try:
    # ── Try importing from the package ──
    sys.path.insert(0, original_cwd)
    try:
        from src.scope import (
            _score_class, _name_parts, _STOP,
            W_BACKTICK_NAME, W_CLASS_NAME_MATCH,
            W_DOTTED_REF, W_CLASS_DOC_MATCH,
        )
    except ImportError:
        # Fallback: define dependencies and function inline
        import re

        W_BACKTICK_NAME = 5.0
        W_CLASS_NAME_MATCH = 6.0
        W_DOTTED_REF = 15.0
        W_CLASS_DOC_MATCH = 2.0

        _STOP = frozenset({
            'this', 'that', 'with', 'from', 'have', 'been', 'will', 'also',
            'when', 'then', 'they', 'them', 'some', 'into', 'more', 'like',
            'such', 'which', 'were', 'each', 'does', 'what', 'about',
            'would', 'should', 'could', 'their', 'there', 'where', 'these',
            'those', 'after', 'before', 'other', 'only', 'using', 'used',
            'code', 'issue', 'error', 'function', 'class', 'method', 'file',
            'line', 'true', 'false', 'none', 'type', 'value', 'object',
            'self', 'args', 'kwargs', 'return', 'raise', 'pass', 'import',
        })

        def _name_parts(name: str) -> set[str]:
            parts = set()
            lower = name.lower()
            parts.add(lower)
            toks = [t for t in lower.split('_') if len(t) > 1]
            for t in toks:
                parts.add(t)
            for i in range(len(toks) - 1):
                parts.add(f"{toks[i]}_{toks[i+1]}")
            for p in re.sub(r'([A-Z])', r'_\1', name).lower().strip('_').split('_'):
                if len(p) > 1:
                    parts.add(p)
            return parts

        def _score_class(cls: dict, signals: dict[str, set[str]]) -> float:
            """Score a class by how well it matches the developer-intent signals."""
            score = 0.0
            name_parts = _name_parts(cls['name'])

            score += len(name_parts & signals['backtick_idents']) * W_BACKTICK_NAME
            score += len(name_parts & signals['plain_idents']) * W_CLASS_NAME_MATCH
            score += len(name_parts & signals['all_words']) * W_CLASS_NAME_MATCH
            score += len(name_parts & signals['dotted_classes']) * W_DOTTED_REF

            # Docstring word overlap with all_words
            if cls['docstring']:
                doc_words = {w for w in re.findall(r'\b([a-zA-Z]{4,})\b',
                                                   cls['docstring'].lower())
                             if w not in _STOP}
                score += len(doc_words & signals['all_words']) * W_CLASS_DOC_MATCH

            return score

    # ── Test case: non-ASCII word in docstring ──
    # 'señor' is a 5-character alphabetic word containing the
    # non-ASCII letter 'ñ'. The ASCII-only regex [a-zA-Z] will
    # not match it, so the function returns 0 instead of the
    # expected W_CLASS_DOC_MATCH.
    non_ascii_word = 'señor'

    cls = {
        'name': 'TestClass',
        'docstring': f'Contains the word {non_ascii_word} in prose.',
    }
    signals = {
        'backtick_idents': set(),
        'plain_idents': set(),
        'all_words': {non_ascii_word},
        'dotted_classes': set(),
    }

    actual = _score_class(cls, signals)
    # Spec says all alphabetic words (including non-ASCII) should match.
    # 'señor' is 5 alphabetic chars, in all_words, not a stop word.
    # Expected: W_CLASS_DOC_MATCH (2.0)
    expected = W_CLASS_DOC_MATCH

    # Bug is confirmed if actual != expected
    passed = actual != expected

    if passed:
        print(f'CONFIRMED — actual: {actual!r} | expected: {expected!r}')
    else:
        print(f'NOT CONFIRMED — actual matched expected: {actual!r}')

except Exception as e:
    print(f'ERROR: {e}')
    import traceback
    traceback.print_exc()
    sys.exit(1)
finally:
    os.chdir(original_cwd)
```

### Probe Output

```
CONFIRMED — actual: 0.0 | expected: 2.0
```

# Bug Report: _score_class

**Source file:** `src/scope-py/_score_class.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- Returns a nonnegative float representing the heuristic relevance of the class
    to the developer intent.
  - The return value is zero when no namepart of the class matches any token in
    'backtick_idents', 'plain_idents', 'dotted_classes', or 'all_words', and no
    alphabetic token of at least 4 characters from the class docstring (excluding
    stop words) matches any token in 'all_words'.
  - Each matching namepart adds an additive weight determined by the signal category
    it matches: tokens matching 'backtick_idents' are weighted higher than tokens
    matching 'dotted_classes', which in turn are weighted higher than tokens
    matching 'plain_idents' or 'all_words'.
  - Each matching docstring token (alphabetic, at least 4 characters, not a stop
    word) that intersects 'all_words' adds an additive weight.
  - The returned score is the sum of all weighted matches across namepart and
    docstring signal intersections. The score increases monotonically with the
    cardinality of matching tokens but respects percategory weight constants, so a
    single match in a highweight category may produce a higher score than multiple
    matches in a lowweight category.

---

### Actual Behavior

The function returns a nonnegative float score computed as the sum of five weighted term contributions from class name and docstring matches against developerintent signals. Let name_parts = _name_parts(cls['name']). Then the returned value equals:
    score = len(name_parts  signals['backtick_idents']) * W_BACKTICK_NAME
          + len(name_parts  signals['plain_idents'])   * W_CLASS_NAME_MATCH
          + len(name_parts  signals['all_words'])      * W_CLASS_NAME_MATCH
          + len(name_parts  signals['dotted_classes']) * W_DOTTED_REF
          + ( 0 if cls['docstring'] == '' else
              len( { w for w in re.findall(r'\\b([a-zA-Z]{4,})\\b', cls['docstring'].lower()) if w not in _STOP }  signals['all_words'] ) * W_CLASS_DOC_MATCH
            ).
  No side effects occur. The constants W_BACKTICK_NAME, W_CLASS_NAME_MATCH, W_DOTTED_REF, W_CLASS_DOC_MATCH and the set _STOP are assumed globally defined.

---

## Code Evidence

```python
Line 15:         doc_words = {w for w in re.findall(r'\b([a-zA-Z]{4,})\b',
Line 16:                                             cls['docstring'].lower())
```

---

## Trigger Condition

The specification requires counting any alphabetic token of at least 4 characters from the docstring (excluding stop words) that intersects 'all_words'. The code uses a regular expression that matches only ASCII letters [a-zA-Z], so it fails to extract tokens containing non-ASCII alphabetic characters (e.g., 'naïve'). Consequently, when such a token is present in 'all_words', the code does not add the weight, violating the specification.

---

## How to trigger the bug

The regex `r'\b([a-zA-Z]{4,})\b'` in `_score_class` (line 364 of `src/scope.py`) only matches ASCII letters. When a class docstring contains a non-ASCII alphabetic token like "naïve" (5 characters, where `ï` is U+00EF, which `str.isalpha()` returns True for), the regex produces zero matches. As a result, the token is not included in `doc_words` and does not contribute to the score even when it is present in `signals['all_words']`.

### Inputs

| Parameter | Value |
|-----------|-------|
| `cls['name']` | `'TestClass'` |
| `cls['docstring']` | `'Handles naïve encoding and decoding'` |
| `signals['all_words']` | `{'naïve'}` |
| Other signal keys | empty sets |

### Expected (spec-correct) Output

`2.0` (one matching token × W_CLASS_DOC_MATCH = 2.0)

### Actual (buggy) Output

`0.0` (regex fails to capture "naïve", so `doc_words` is empty)

### How to Reproduce

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
from src.scope import _score_class

cls = {'name': 'TestClass', 'docstring': 'Handles naïve encoding and decoding'}
signals = {
    'backtick_idents': set(),
    'plain_idents': set(),
    'all_words': {'naïve'},
    'dotted_classes': set(),
}
actual = _score_class(cls, signals)
# actual (buggy) output: 0.0
# expected (correct) output: 2.0
```

---

## Probe Script

```python
import sys
sys.path.insert(0, '.')

try:
    from src.scope import _score_class

    # Class with non-ASCII word in docstring: "naive" (5 chars, contains 'i' = U+00EF)
    # The regex r'\b([a-zA-Z]{4,})\b' on line 364 only matches ASCII [a-zA-Z],
    # so it will NOT extract "naive" despite it being alphabetic (isalpha()=True)
    cls = {
        'name': 'TestClass',
        'docstring': 'Handles naïve encoding and decoding',
    }

    # signals with "naive" explicitly in all_words (spec allows any alphabetic token)
    signals = {
        'backtick_idents': set(),
        'plain_idents': set(),
        'all_words': {'naïve'},
        'dotted_classes': set(),
    }

    actual = _score_class(cls, signals)

    # Per spec: each matching docstring token (alphabetic, >=4 chars, not stop word)
    # that intersects all_words adds W_CLASS_DOC_MATCH (2.0) per match.
    # "naive" is 5 chars, alphabetic (Python str.isalpha() = True), NOT in _STOP.
    # Expected: 2.0 (one token x W_CLASS_DOC_MATCH)
    # Actual:   0.0 (regex fails to capture non-ASCII characters)
    expected = 2.0

    passed = actual != expected
except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)

if passed:
    print(f'CONFIRMED - actual: {actual!r} | expected: {expected!r}')
else:
    print(f'NOT CONFIRMED - actual matched expected: {actual!r}')
```

### Probe Output

```
CONFIRMED - actual: 0.0 | expected: 2.0
```

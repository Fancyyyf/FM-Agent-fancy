# Bug Report: _base_score

**Source file:** `/tmp/fm_agent_wt_FM-Agent_dlsr6ukl/snapshot/fm_agent/extracted_functions/src/scope-py/_base_score.py`
**Original source:** `src/scope.py`, line 392
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- Returns a non-negative float representing the heuristic relevance of
    the function to the developer intent described by signals
  - The score is the sum of weighted contributions from multiple signal
    categories:
    (a) a contribution when name matches a traceback function name
        (case-insensitive) or when a component of name matches one
    (b) contributions proportional to the size of the set intersection
        between name components and backtick identifiers, dotted-reference
        method names, and plain prose identifiers, each category carrying
        a distinct pre-defined weight
    (c) a contribution proportional to the intersection between name
        components of length  5 characters and alphabetic prose words
        from the intent
    (d) a typo-tolerant contribution that applies only when a name
        component and an intent word both have length  5 characters and
        a similarity ratio of at least 75%
    (e) a contribution proportional to the intersection between exception
        type names referenced in the function body and exception types
        mentioned in the intent
    (f) a contribution equal to the count of body words overlapping with
        intent prose words, divided by the square root of body_lines,
        multiplied by a pre-defined weight
  - Each intersection-based contribution is linear in the size of the
    overlap
  - Returns 0.0 when every signal token set relevant to the scoring
    categories has an empty intersection with the corresponding function
    textual element

---

### Actual Behavior

The function returns a float value computed as follows. Let parts = _name_parts(name) (the set of lowercased name components). Let specific_name_words = {p in parts | len(p) >= 5}. The returned score is the sum of: (i) W_TRACEBACK * |{tf in signals['traceback_funcs'] | tf.lower() == name.lower() or tf.lower() in parts}|; (ii) W_BACKTICK_NAME * |parts  signals['backtick_idents']|; (iii) W_BACKTICK_BODY * |idents  signals['backtick_idents']|; (iv) W_DOTTED_REF * |parts  signals['dotted_refs']|; (v) W_PLAIN_NAME * |parts  signals['plain_idents']|; (vi) W_NAME_ALL_WORDS * |specific_name_words  signals['all_words']|; (vii) _fuzzy_name_score(parts, signals); (viii) if signals['exception_types']   and exc_types   then W_EXCEPTION_MATCH * |signals['exception_types']  exc_types| else 0; (ix) W_BODY_WORDS * (|body_words  signals['all_words']|) / max(body_lines, 1)^{0.5}. The score is non-negative. The function terminates normally (no exceptions) under the given pre-conditions. Formally, result = W_TRACEBACK|{tf  signals['traceback_funcs'] : tf.lower() = name.lower()  tf.lower()  parts}| + W_BACKTICK_NAME|parts  signals['backtick_idents']| + W_BACKTICK_BODY|idents  signals['backtick_idents']| + W_DOTTED_REF|parts  signals['dotted_refs']| + W_PLAIN_NAME|parts  signals['plain_idents']| + W_NAME_ALL_WORDS|{p  parts : |p|  5}  signals['all_words']| + _fuzzy_name_score(parts, signals) + (W_EXCEPTION_MATCH|signals['exception_types']  exc_types| if signals['exception_types']    exc_types   else 0) + W_BODY_WORDS|body_words  signals['all_words']| / max(body_lines, 1)^{0.5}.

---

## Code Evidence

Line 16

---

## Trigger Condition

The code adds a contribution from body identifiers intersecting with backtick identifiers (W_BACKTICK_BODY * |idents  backtick_idents|), which is not listed among the specification's permitted categories. For the given input, the code returns W_BACKTICK_BODY > 0 while the specification requires 0.

---

## How to trigger the bug

The `_base_score` function in `src/scope.py` (line 392) adds an extra contribution
`len(idents & signals['backtick_idents']) * W_BACKTICK_BODY` that is not listed
among the permitted scoring categories in the specification. Category (b) of the
spec only permits intersections between **name components** (`parts`) and
backtick identifiers, dotted-reference method names, and plain prose identifiers.
The code additionally intersects **body identifiers** (`idents`) with backtick
identifiers, inflating the score when a function body references identifiers
that also appear in backtick/code-fence spans of the developer-intent text.

### Inputs

| Parameter | Value |
|-----------|-------|
| `name` | `"foo"` |
| `idents` | `{"parse", "token"}` |
| `body_words` | `set()` |
| `exc_types` | `set()` |
| `body_lines` | `10` |
| `signals['traceback_funcs']` | `set()` |
| `signals['backtick_idents']` | `{"parse", "token"}` |
| `signals['dotted_refs']` | `set()` |
| `signals['plain_idents']` | `set()` |
| `signals['all_words']` | `set()` |
| `signals['exception_types']` | `set()` |

### Expected (spec-correct) Output

`0.0`

### Actual (buggy) Output

`4.0`

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import sys
sys.path.insert(0, '.')
from src.scope import _base_score

actual = _base_score(
    name="foo",
    idents={"parse", "token"},
    body_words=set(),
    exc_types=set(),
    body_lines=10,
    signals={
        'traceback_funcs': set(),
        'backtick_idents': {"parse", "token"},
        'dotted_refs': set(),
        'plain_idents': set(),
        'all_words': set(),
        'exception_types': set(),
    },
)
# actual (buggy) output: 4.0
# expected (correct) output: 0.0
```

---

## Probe Script

```python
import sys
sys.path.insert(0, '.')
try:
    from src.scope import _base_score

    # Construct inputs that trigger the W_BACKTICK_BODY bug.
    # The spec only permits name-component ↔ backtick_idents intersections (T2).
    # The buggy code also adds body-ident ↔ backtick_idents (T2b), which contributes
    # W_BACKTICK_BODY * |idents ∩ backtick_idents| = 2.0 * 2 = 4.0.
    #
    # We choose a name with zero overlap with any signal category, and idents that
    # DO overlap with backtick_idents. All other signal categories are empty so
    # every permitted intersection is zero. The spec requires 0.0;
    # the buggy code returns > 0.0.

    name = "foo"
    idents = {"parse", "token"}
    body_words = set()
    exc_types = set()
    body_lines = 10
    signals = {
        'traceback_funcs': set(),
        'backtick_idents': {"parse", "token"},
        'dotted_refs': set(),
        'plain_idents': set(),
        'all_words': set(),
        'exception_types': set(),
    }

    actual = _base_score(name, idents, body_words, exc_types, body_lines, signals)
    expected = 0.0  # spec-correct: no permitted category has any overlap

    passed = actual != expected
except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)

if passed:
    print(f'CONFIRMED — actual: {actual!r} | expected: {expected!r}')
else:
    print(f'NOT CONFIRMED — actual matched expected: {actual!r}')
```

### Probe Output

```
CONFIRMED — actual: 4.0 | expected: 0.0
```

# Bug Report: _name_parts

**Source file:** `src/scope-py/_name_parts.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

Returns a set of lowercase strings, each being a word-level constituent of name obtained by decomposition at word boundaries. The set always contains the full name in lowercase. Additionally, the set contains: (a) individual tokens of two or more characters produced by splitting name on underscore separators; (b) each consecutive two-token compound of those underscore-split tokens, joined by an underscore; (c) individual tokens of two or more characters produced by splitting name at transitions from a lowercase letter to an uppercase letter. Tokens shorter than two characters are excluded from the decomposition-derived members; the full lowercased name is always included regardless of length. Every returned string consists solely of lowercase ASCII letters and underscores, with no internal delimiters other than underscores in the two-token compounds. The set is never empty and is deterministic: identical input always produces identical output.

---

### Actual Behavior

The function returns a set of strings derived from the input name. Let s = name.lower(), T = { t for t in s.split('_') if len(t) > 1 }, C = { toks[i] + '_' + toks[i+1] for i in range(len(toks)-1) } where toks = [ t for t in s.split('_') if len(t) > 1 ] (preserving order), and P = { p for p in re.sub(r'([A-Z])', r'_\\1', name).lower().strip('_').split('_') if len(p) > 1 }. Then the returned set equals {s} ∪ T ∪ C ∪ P.

---

## Code Evidence

Line 19: `for p in re.sub(r'([A-Z])', r'_\\1', name).lower().strip('_').split('_'):`

---

## Trigger Condition

The code uses CamelCase splitting that inserts underscores before every uppercase letter, which breaks uppercase acronyms into single-character fragments that are filtered out (e.g., 'XMLHttp' becomes single letters 'x','m','l','http', only 'http' survives). The specification requires splitting only at transitions from a lowercase letter to an uppercase letter, so 'XMLHttp' should be kept intact as 'xmlhttp'.

---

## How to trigger the bug

Call `_name_parts('XMLHttp')`. The buggy code splits at every uppercase letter (`r'([A-Z])'`), producing single-letter fragments `'x'`, `'m'`, `'l'` that get filtered by `len(p) > 1`. Only `'http'` survives, adding a spurious token to the result set. The spec requires CamelCase splitting only at lowercase→uppercase transitions, which would leave `'XMLHttp'` intact as `'xmlhttp'`.

### Inputs

| Parameter | Value |
|-----------|-------|
| name | `'XMLHttp'` |

### Expected (spec-correct) Output

`{'xmlhttp'}`

### Actual (buggy) Output

`{'xmlhttp', 'http'}`

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
>>> from src.scope import _name_parts
>>> _name_parts('XMLHttp')
{'xmlhttp', 'http'}
# actual (buggy) output: {'xmlhttp', 'http'}
# expected (correct) output: {'xmlhttp'}
```

---

## Probe Script

```python
"""Probe script for bug: src--scope-py--_name_parts

The function _name_parts splits CamelCase at EVERY uppercase letter instead of
only at lowercase→uppercase transitions. This breaks all-caps acronyms like
'XMLHttp' where 'XML' gets split into single-character fragments that are
filtered out (len > 1), leaving only 'http'.

Spec requires: splitting only at transitions from lowercase to uppercase.
Buggy behavior: splitting at every uppercase letter.
"""

import sys
sys.path.insert(0, '.')

try:
    from src.scope import _name_parts

    name = 'XMLHttp'
    result = _name_parts(name)

    # Spec-correct expected: no lowercase→uppercase transitions in 'XMLHttp',
    # so CamelCase split should produce {'xmlhttp'} only.
    # Buggy behavior: every uppercase gets a '_' prepended, producing
    # 'x', 'm', 'l', 'http' → only 'http' survives len>1 filter.
    # The full lowercased name 'xmlhttp' is always included regardless.

    expected_missing = {'xmlhttp'}
    expected = expected_missing  # full name always included
    buggy_extra = 'http'

    # Bug is confirmed if 'http' appears in result (broken CamelCase split)
    # when it shouldn't (no lower→upper transition exists)
    if buggy_extra in result:
        print(f'CONFIRMED — actual result contains unexpected token {buggy_extra!r} '
              f'from broken CamelCase split | expected: {expected!r}')
    else:
        print(f'NOT CONFIRMED — result={result!r}, no unexpected CamelCase token found')

except Exception as e:
    print(f'ERROR: {e}')
    import traceback
    traceback.print_exc()
    sys.exit(1)
```

### Probe Output

```
CONFIRMED — actual result contains unexpected token 'http' from broken CamelCase split | expected: {'xmlhttp'}
```

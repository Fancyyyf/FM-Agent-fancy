# Bug Report: _base_score

**Source file:** `src/scope-py/_base_score.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

The specification requires that only the full name is tested case-insensitively against traceback-function signals. The code additionally matches any traceback function name against individual name parts, causing a false positive contribution (W_TRACEBACK) when a part (but not the full name) matches a traceback function.

---

### Actual Behavior

The code checks `tf.lower() == name.lower() or tf.lower() in parts`, which means if any traceback function name matches a single word/piece of the function name (via `_name_parts` decomposition), the function receives the full `W_TRACEBACK` weight, even when the full function name does not match any traceback function.

---

## Code Evidence

Line 11: `if tf.lower() == name.lower() or tf.lower() in parts:`

---

## Trigger Condition

The specification requires that only the full name is tested case-insensitively against traceback-function signals. The code additionally matches any traceback function name against individual name parts, causing a false positive contribution (W_TRACEBACK) when a part (but not the full name) matches a traceback function.

---

## How to trigger the bug

When a traceback function name matches a component word within a decomposed function name (e.g., "sort" within "some_sort_data") but does NOT match the full function name, the code incorrectly awards the `W_TRACEBACK` weight. The spec requires only full-name matching.

### Inputs

| Parameter | Value |
|-----------|-------|
| `name` | `"some_sort_data"` |
| `idents` | `set()` (empty) |
| `body_words` | `set()` (empty) |
| `exc_types` | `set()` (empty) |
| `body_lines` | `1` |
| `signals['traceback_funcs']` | `{"sort"}` |
| All other signal sets | `set()` (empty) |

### Expected (spec-correct) Output

`0.0`

### Actual (buggy) Output

`10.0`

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import sys
sys.path.insert(0, '.')

from src.scope import _base_score

empty = set()
name = "some_sort_data"
signals = {
    'traceback_funcs': {"sort"},
    'backtick_idents': empty,
    'dotted_refs': empty,
    'plain_idents': empty,
    'exception_types': empty,
    'all_words': empty,
}

score = _base_score(name, empty, empty, empty, 1, signals)
print(score)
# actual (buggy) output: 10.0
# expected (correct) output: 0.0
```

---

## Probe Script

```python
import sys
import os

# ── Load the package via its public entry point ───────────────────────────────
# Run from repo root: sys.path[0] handles the import chain
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'src')))

try:
    import scope as scope_module
except ImportError:
    # The module has relative imports (.extract, .llm_client); try as a package
    try:
        import src.scope as scope_module
    except ImportError as e2:
        print(f'ERROR: Could not import scope module: {e2}')
        sys.exit(1)

_base_score = scope_module._base_score

# ── Bug test: traceback function name matches a NAME PART but NOT the full name ──
# The spec claims that only the full name is tested case-insensitively against
# traceback-function signals. The code additionally matches individual name parts
# (line 385: tf.lower() in parts), causing a false positive W_TRACEBACK contribution.

empty = set()

# name "some_sort_data" decomposes via _name_parts into parts including "sort"
# signals['traceback_funcs'] contains "sort" — a part match but NOT a full-name match
name = "some_sort_data"
signals = {
    'traceback_funcs': {"sort"},
    'backtick_idents': empty,
    'dotted_refs': empty,
    'plain_idents': empty,
    'exception_types': empty,
    'all_words': empty,
}

try:
    actual = _base_score(name, empty, empty, empty, 1, signals)
    # Expected: 0.0 — only the full name should be tested against traceback_funcs.
    # "sort" != "some_sort_data", so no match should occur.
    expected = 0.0
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
CONFIRMED — actual: 10.0 | expected: 0.0
```

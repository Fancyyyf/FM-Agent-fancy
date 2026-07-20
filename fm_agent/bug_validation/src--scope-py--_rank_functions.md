# Bug Report: _rank_functions

**Source file:** `src/scope.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- Returns a list of dicts with the same cardinality as funcs_info,
    containing exactly one entry per element of funcs_info. Each entry
    contains at minimum 'name' (str), 'start' (int, 1-based), 'end' (int,
    1-based), and 'score' (float, non-negative).
  - The list is sorted in descending order by 'score'.
  - Every 'start' value in the result matches exactly one 'start' from
    funcs_info; no entries are added, removed, or duplicated.
  - Each function's score is the sum of:
    (a) a base relevance score proportional to weighted matches between the
        function's name and body tokens against the signal token sets,
        normalized by the function's line count;
    (b) a call-graph propagation bonus: for every function whose base
        relevance score is positive, a fixed fraction of that score is added
        to the score of every function it calls and every function that calls
        it, identified by name within funcs_info;
    (c) when classes is non-empty, a class-scope bonus: for every class that
        is deemed relevant to the signals, each of its methods receives a
        bonus proportional to the class's relevance, subject to an upper
        bound on the per-method bonus.
  - Call-graph bonuses accumulate additively across all caller/callee
    relationships within the file.

---

### Actual Behavior

The function returns a list `result` such that:

- `result` contains exactly the same dictionary objects as the input list `funcs_info`, in descending order of their `'score'` values (i.e., sorted using the key `lambda x: -x['score']` with stable sorting).
- Every dictionary `f` in `funcs_info` has been mutated in place to contain a key `'score'` whose value is the final computed score, a nonnegative float.
- The final score for a function `f` is defined as:

  final_score(f) = base(f) + B(f) + C(f)

  where:
  * base(f) = _base_score(f['name'], f['idents'], f['body_words'], f['exc_types'], f['end'] - f['start'] + 1, signals).
  * B(f) is the callgraph propagation bonus summed over all direct callee and caller relations:
      - For every function `g` in `funcs_info` with `base(g) > 0`:
            For every `callee_name` in `g['calls']`, and for every `h` in `funcs_info` with `h['name'] == callee_name` and `h['start']` equal to `f['start']`, add `base(g) * CALLEE_INHERIT` to B(f).
            For every `h` in `funcs_info` such that `g['name']` is in `h['calls']` and `h['start']` equals `f['start']`, add `base(g) * CALLER_INHERIT` to B(f).
    (Thus, B(f) accumulates contributions from every caller and callee of functions that have the same start line as f.)
  * C(f) is the classscope bonus:
      - If `classes` is truthy (nonempty):
           For every class dictionary `cls` in `classes`:
                 Let `score_cls = _score_class(cls, signals)`.
                 If `score_cls > 0`:
                     raw = `score_cls * CLASS_METHOD_INHERIT`
                     capped = `min(raw, CLASS_BOOST_CAP)`
                     For every `lineno` in `cls['method_linenos']` that equals `f['start']`, add `capped` to C(f).
      - Otherwise (zero or false `classes`), C(f) = 0.

- No exceptions are raised under the given preconditions; the function always executes to completion.
- The input arguments `funcs_info` and `classes` may be mutated in place (the caller should not rely on their values after the call).

---

## Code Evidence

```python
# src/scope.py

CALLEE_INHERIT = 0.30          # line 93
CALLER_INHERIT = 0.20          # line 94

def _rank_functions(funcs_info, classes, signals):
    ...
    # ── 1. call-graph propagation ──
    for f in funcs_info:
        bscore = f['score']
        if bscore <= 0:
            continue
        for called_name in f['calls']:
            for tl in name_to_linenos.get(called_name, []):
                bonus[tl] += bscore * CALLEE_INHERIT    # line 450 — callee propagation
        for other in funcs_info:
            if f['name'] in other['calls']:
                bonus[other['start']] += bscore * CALLER_INHERIT  # line 453 — caller propagation
```

The specification demands **"a fixed fraction"** (singular) for both callee and caller propagation. The code uses two distinct constants (`CALLEE_INHERIT = 0.30`, `CALLER_INHERIT = 0.20`), violating the requirement.

---

## Trigger Condition

The specification describes a callgraph bonus where a single fixed fraction of the base score is added to every callee and every caller. The code uses two potentially different constants (CALLEE_INHERIT and CALLER_INHERIT), allowing the fractions to differ, which violates the requirement when they are not equal.

---

## How to trigger the bug

When a function `A` has a positive base score and both calls another function `B` and is called by another function `C`, the call-graph propagation applies `CALLEE_INHERIT` (0.30) to `B`'s bonus and `CALLER_INHERIT` (0.20) to `C`'s bonus. Per the specification, both should use the same fraction.

### Inputs

| Parameter | Value |
|-----------|-------|
| funcs_info | `[{'name': 'A', 'calls': {'B'}, 'start': 1, ...}, {'name': 'B', 'calls': set(), 'start': 10, ...}, {'name': 'C', 'calls': {'A'}, 'start': 20, ...}]` |
| classes | `[]` |
| signals | `{}` |
| A's base score | `10.0` (controlled via monkeypatch) |
| B and C base scores | `0.0` |

### Expected (spec-correct) Output

With a single fixed fraction for both directions, functions `B` and `C` would receive **equal** bonuses from `A`'s base score. If the spec's "fixed fraction" were 0.30, both would get `10.0 * 0.30 = 3.0`. If it were 0.20, both would get `2.0`. Either way, their scores would be **equal**.

### Actual (buggy) Output

- `B` (callee of A) receives bonus: `10.0 * 0.30 = 3.0`
- `C` (caller of A) receives bonus: `10.0 * 0.20 = 2.0`
- `B.score (3.0) ≠ C.score (2.0)` → **violates the spec**

### How to Reproduce

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import sys; sys.path.insert(0, '.')
from src.scope import _rank_functions, CALLEE_INHERIT, CALLER_INHERIT

# Patch _base_score to isolate the call-graph propagation logic
import src.scope as scope_mod
original = scope_mod._base_score
scope_mod._base_score = lambda name, *a: 10.0 if name == 'A' else 0.0

funcs_info = [
    {'name': 'A', 'start': 1,  'end': 5,  'idents': set(),
     'body_words': set(), 'exc_types': set(), 'calls': {'B'}},
    {'name': 'B', 'start': 10, 'end': 15, 'idents': set(),
     'body_words': set(), 'exc_types': set(), 'calls': set()},
    {'name': 'C', 'start': 20, 'end': 25, 'idents': set(),
     'body_words': set(), 'exc_types': set(), 'calls': {'A'}},
]
result = _rank_functions(funcs_info, [], {})
scope_mod._base_score = original

b = next(f['score'] for f in result if f['name'] == 'B')
c = next(f['score'] for f in result if f['name'] == 'C')
print(f'B score: {b}, C score: {c}')
# actual (buggy) output: B score: 3.0, C score: 2.0
# expected (correct) output: B score == C score (both use same fraction)
```

---

## Probe Script

```python
"""Probe for bug: _rank_functions uses CALLEE_INHERIT != CALLER_INHERIT,
violating the spec that requires "a fixed fraction" (singular, same for both)."""

import sys
import os

# Script is run from repo root; ensure '.' is on sys.path so 'src' is importable
sys.path.insert(0, os.getcwd())

try:
    # Load via the package entry point
    from src.scope import _rank_functions, CALLEE_INHERIT, CALLER_INHERIT
except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)

try:
    import src.scope as scope_mod

    # Patch _base_score to return controlled values so we isolate the
    # call-graph propagation logic.
    def mock_base_score(name, _idents, _body_words, _exc_types, _loc, _signals):
        # A has positive base score; B and C start at zero.
        scores = {'A': 10.0}
        return scores.get(name, 0.0)

    original_base_score = scope_mod._base_score
    scope_mod._base_score = mock_base_score

    # ── Test scenario ────────────────────────────────────────────────
    # A (score=10) calls B  →  B gets  10 * CALLEE_INHERIT  (callee direction)
    # A (score=10) is called by C  →  C gets  10 * CALLER_INHERIT  (caller direction)
    #
    # Spec says "a fixed fraction" (same for both).  Code uses two constants.
    # BUG: if CALLEE_INHERIT != CALLER_INHERIT then B_score != C_score
    #      but the spec requires them to be equal.

    funcs_info = [
        {'name': 'A', 'start': 1,  'end': 5,  'idents': set(),
         'body_words': set(), 'exc_types': set(), 'calls': {'B'}},
        {'name': 'B', 'start': 10, 'end': 15, 'idents': set(),
         'body_words': set(), 'exc_types': set(), 'calls': set()},
        {'name': 'C', 'start': 20, 'end': 25, 'idents': set(),
         'body_words': set(), 'exc_types': set(), 'calls': {'A'}},
    ]

    signals: dict[str, set[str]] = {}
    classes: list[dict] = []

    result = _rank_functions(funcs_info, classes, signals)

    # Restore the original function
    scope_mod._base_score = original_base_score

    # Look up final scores
    result_map = {f['name']: f['score'] for f in result}
    b_score  = result_map['B']  # should be 10 * CALLEE_INHERIT   = 3.0
    c_score  = result_map['C']  # should be 10 * CALLER_INHERIT   = 2.0
    a_score  = result_map['A']  # should be 10 + 10*CALLER_INHERIT (since C's base is 0, no propagation FROM C)

    # Bug: callee and caller get different bonus fractions
    expected_callee_bonus = 10.0 * CALLEE_INHERIT
    expected_caller_bonus = 10.0 * CALLER_INHERIT

    callee_discrepancy = abs(b_score - expected_callee_bonus)
    caller_discrepancy = abs(c_score - expected_caller_bonus)

    # Both discrepancies should be negligible AND the two bonuses should differ
    fractions_differ = abs(b_score - c_score) > 0.001

    inputs_ok = callee_discrepancy < 0.001 and caller_discrepancy < 0.001
    passed = inputs_ok and fractions_differ

    if passed:
        print(f'CONFIRMED — callee bonus ({b_score!r}) ≠ caller bonus ({c_score!r})')
        print(f'  CALLEE_INHERIT = {CALLEE_INHERIT!r}')
        print(f'  CALLER_INHERIT = {CALLER_INHERIT!r}')
        print(f'  Spec requires "a fixed fraction" (singular) for both directions.')
    else:
        print(f'NOT CONFIRMED — B score: {b_score!r}, C score: {c_score!r}')
        print(f'  callee_discrepancy={callee_discrepancy!r}, caller_discrepancy={caller_discrepancy!r}')

except Exception as e:
    import traceback
    traceback.print_exc()
    print(f'ERROR: {e}')
    sys.exit(1)
```

### Probe Output

```
CONFIRMED — callee bonus (3.0) ≠ caller bonus (2.0)
  CALLEE_INHERIT = 0.3
  CALLER_INHERIT = 0.2
  Spec requires "a fixed fraction" (singular) for both directions.
```

# Bug Report: _rank_functions

**Source file:** `/home/fancy/Projects_Vault/FM-Agent/fm_agent/extracted_functions/src/scope-py/_rank_functions.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

Returns a list containing every dict from funcs_info, each augmented with a 'score' key holding a non-negative float. The list is sorted in descending order by score. The final score for each entry is the sum of three additive components: (1) a weighted multi-tier heuristic match between the entry's metadata and the signal token sets  with traceback-function-name signals weighted highest, followed by dotted-reference signals, then backtick-identifier matches in name and body, plain-identifier overlap in name, exception-type signals found in the entry's exception types, and body-word overlap with intent tokens scaled inversely by the square root of the function's body line count; (2) a one-hop call-graph enrichment where, for every function with a positive unenriched score, each function whose name appears in that function's 'calls' list receives a fixed fraction of the caller's unenriched score, and each function that lists that function's name in its own 'calls' list receives a smaller fixed fraction of the callee's unenriched score; and (3) when classes is non-empty, a class-scope enrichment where member functions of classes whose name and docstring tokens overlap with signal tokens receive a per-method additive bonus that is proportional to a class-level match score and capped at a fixed maximum value per method. Two entries with the same name and the same 'start' line number (signifying duplicate entries) are scored independently.

---

### Actual Behavior

Natural language: After execution, the input list `funcs_info` is unchanged in length and order; each dictionary in it has been augmented with a new key `'score'` whose value is a non-negative float. The `classes` list and `signals` dictionary are not modified. The return value is a new list containing exactly the same dictionary objects, sorted in descending order by their `'score'` values (i.e., from highest to lowest score). The final `'score'` for each function is the sum of a base score (derived from signalmatching heuristics) and nonnegative bonuses from intrafile callgraph propagation and classscope narrowing, applied additively. No exceptions are raised. Formal logic: let `F = funcs_info` (the original list) and `n = len(F)`. Then (1) for all `i{0,,n-1}`, `F[i]` is the same dictionary object and `F[i]['score']` is a real number  0; (2) `classes = old(classes)` and `signals = old(signals)`, i.e., they are unchanged; (3) the return value `R` is a list of length `n` such that `j{0,,n-1}`, `R[j]` is one of the dictionaries from `F`, the multiset of dictionary identities in `R` equals that in `F`, and `j{0,,n-2}`, `R[j]['score']  R[j+1]['score']`; (4) no unhandled exception occurs.

---

## Code Evidence

Line 17: name_to_linenos: dict[str, list[int]] = defaultdict(list)
Line 18: for f in funcs_info:
Line 19: name_to_linenos[f['name']].append(f['start'])
Line 26: for tl in name_to_linenos.get(called_name, []):
Line 27: bonus[tl] += bscore * CALLEE_INHERIT
Line 32: f['score'] += bonus[f['start']]

---

## Trigger Condition

The specification explicitly requires that duplicate entries (same name and same 'start' line) be scored independently. The call-graph propagation code (lines 17-19, 26-27, 32) uses a bonus dictionary keyed only by start line, collapsing duplicate entries into a single bonus accumulator. When a caller calls a function that appears as duplicate entries, the bonus for that start line is incremented multiple times, inflating the score for all duplicates sharing that start line and violating independent scoring.

---

## How to trigger the bug

The probe creates two duplicate entries (both named "helper" with the same start line 50) and one caller that calls "helper". Because `name_to_linenos["helper"]` collects both entries, iterating it during call-graph propagation doubles the callee bonus.

### Inputs

| Parameter | Value |
|-----------|-------|
| funcs_info[0] (helper_a) | `{'name': 'helper', 'start': 50, 'end': 60, 'calls': []}` |
| funcs_info[1] (helper_b) | `{'name': 'helper', 'start': 50, 'end': 60, 'calls': []}` (duplicate) |
| funcs_info[2] (caller) | `{'name': 'caller', 'start': 100, 'end': 110, 'calls': ['helper']}` |
| classes | `[]` (empty) |
| signals | `traceback_funcs={'helper', 'caller'}`, all others empty |

### Expected (spec-correct) Output

Both helper entries should receive `base_score + caller_base_score * CALLEE_INHERIT` applied exactly once:

- helper_a score = `10.0 + 10.0 * 0.30 = 13.0` (independently scored)
- helper_b score = `10.0 + 10.0 * 0.30 = 13.0` (independently scored)

### Actual (buggy) Output

Both helper entries get bonus doubled because `name_to_linenos["helper"] = [50, 50]` causes two iterations over the same start line:

- helper_a score = `10.0 + 10.0 * 0.30 * 2 = 16.0` (inflated)
- helper_b score = `10.0 + 10.0 * 0.30 * 2 = 16.0` (inflated)

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
from src.scope import _rank_functions, CALLEE_INHERIT, W_TRACEBACK

signals = {
    'traceback_funcs': {'helper', 'caller'},
    'backtick_idents': set(), 'dotted_refs': set(), 'dotted_classes': set(),
    'plain_idents': set(), 'all_words': set(), 'exception_types': set(),
}

helper_a = {'name': 'helper', 'start': 50, 'end': 60, 'idents': set(),
            'body_words': set(), 'exc_types': set(), 'calls': []}
helper_b = {'name': 'helper', 'start': 50, 'end': 60, 'idents': set(),
            'body_words': set(), 'exc_types': set(), 'calls': []}  # duplicate
caller   = {'name': 'caller', 'start': 100, 'end': 110, 'idents': set(),
            'body_words': set(), 'exc_types': set(), 'calls': ['helper']}

result = _rank_functions([helper_a, helper_b, caller], [], signals)
for f in result:
    if f['name'] == 'helper':
        print(f"score={f['score']}")  # actual (buggy) output: 16.0
                                       # expected (correct) output: 13.0
```

---

## Probe Script

```python
"""Probe for bug: _rank_functions call-graph propagation inflates duplicate-entry scores
because the bonus dictionary is keyed only by start line and name_to_linenos
collects duplicate start lines for the same name.

Bug ID: src--scope-py--_rank_functions
"""

import os
import sys
import tempfile
from pathlib import Path

# Ensure the repo root is importable
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

# Save and sanitize environment to isolate the test
_saved_env = {k: os.environ.get(k) for k in (
    "FM_AGENT_CONFIG", "LLM_API_KEY", "LLM_API_BASE_URL", "FM_AGENT_MODEL_BACKEND",
    "LLM_MODEL", "LLM_EFFORT", "OPENCODE_MODEL_PROVIDER", "LLM_API_STYLE",
    "MAX_SPC_ITER", "GRANULARITY", "MAX_WORKERS", "OPENCODE_MAX_RETRIES",
    "BUG_VALIDATION_MAX_RETRIES", "OPENCODE_TIMEOUT_SECONDS",
    "FM_AGENT_DOMAIN_KNOWLEDGE",
)}
for k in _saved_env:
    if k in os.environ:
        del os.environ[k]

try:
    from src.scope import _rank_functions, CALLEE_INHERIT, CALLER_INHERIT, W_TRACEBACK

    # ── Setup: minimal signals so only traceback naming gives base score ──
    signals: dict[str, set[str]] = {
        'traceback_funcs': {'helper', 'caller'},
        'backtick_idents': set(),
        'dotted_refs': set(),
        'dotted_classes': set(),
        'plain_idents': set(),
        'all_words': set(),
        'exception_types': set(),
    }

    # Two duplicate entries: same name "helper", same start line 50
    # Both will receive base_score = W_TRACEBACK (10.0) from traceback_funcs match
    helper_a = {
        'name': 'helper',
        'start': 50,
        'end': 60,
        'idents': set(),
        'body_words': set(),
        'exc_types': set(),
        'calls': [],
    }
    helper_b = {
        'name': 'helper',
        'start': 50,          # duplicate — same name, same start line
        'end': 60,
        'idents': set(),
        'body_words': set(),
        'exc_types': set(),
        'calls': [],
    }
    # A caller with positive score that calls "helper"
    caller = {
        'name': 'caller',
        'start': 100,
        'end': 110,
        'idents': set(),
        'body_words': set(),
        'exc_types': set(),
        'calls': ['helper'],
    }

    funcs_info: list[dict] = [helper_a, helper_b, caller]
    classes: list[dict] = []

    # ── Execute ──
    result = _rank_functions(funcs_info, classes, signals)

    # ── Verify ──
    helpers = [f for f in result if f['name'] == 'helper']
    callers  = [f for f in result if f['name'] == 'caller']

    if len(helpers) != 2:
        print(f"ERROR: expected 2 helper entries in result, got {len(helpers)}")
        sys.exit(1)
    if len(callers) != 1:
        print(f"ERROR: expected 1 caller entry in result, got {len(callers)}")
        sys.exit(1)

    actual_scores = sorted(h['score'] for h in helpers)
    # The call-graph propagation uses bscore = f['score'] (the base score,
    # set BEFORE bonus application).  For the caller this is W_TRACEBACK = 10.0.
    caller_base_score = W_TRACEBACK  # 10.0

    # Expected base score per helper: W_TRACEBACK = 10.0
    base_score = W_TRACEBACK  # 10.0

    # Independent scoring: caller calls "helper" ⇒ each helper should get
    # base_score + caller_base_score * CALLEE_INHERIT applied EXACTLY ONCE.
    # With the bug, name_to_linenos["helper"] = [50, 50] causes the bonus
    # to be incremented twice, so actual = base_score + caller_base_score * CALLEE_INHERIT * 2.
    expected_independent = base_score + caller_base_score * CALLEE_INHERIT
    buggy_inflated       = base_score + caller_base_score * CALLEE_INHERIT * 2

    tolerance = 0.001

    # Check whether actual scores match the buggy (inflated) prediction
    both_buggy = all(abs(s - buggy_inflated) < tolerance for s in actual_scores)

    if both_buggy:
        print(
            f"CONFIRMED — duplicate entries share inflated call-graph bonus: "
            f"actual scores={actual_scores!r} | "
            f"expected (independent, bonus applied once)={expected_independent!r} | "
            f"buggy (bonus doubled)={buggy_inflated!r} | "
            f"caller_base_score={caller_base_score!r}, CALLEE_INHERIT={CALLEE_INHERIT!r}"
        )
    else:
        print(
            f"NOT CONFIRMED — actual scores did not match buggy (doubled-bonus) prediction: "
            f"actual scores={actual_scores!r} | "
            f"expected independent={expected_independent!r} | "
            f"buggy inflated={buggy_inflated!r}"
        )

except Exception as e:
    import traceback
    traceback.print_exc()
    print(f"ERROR: {e}")
    sys.exit(1)

finally:
    # Restore environment
    for k, v in _saved_env.items():
        if v is not None:
            os.environ[k] = v
        elif k in os.environ:
            del os.environ[k]
```

### Probe Output

```
CONFIRMED — duplicate entries share inflated call-graph bonus: actual scores=[16.0, 16.0] | expected (independent, bonus applied once)=13.0 | buggy (bonus doubled)=16.0 | caller_base_score=10.0, CALLEE_INHERIT=0.3
```

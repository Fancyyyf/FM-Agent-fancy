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

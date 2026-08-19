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

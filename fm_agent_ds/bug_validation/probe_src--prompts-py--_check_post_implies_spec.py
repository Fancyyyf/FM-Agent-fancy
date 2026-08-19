"""Probe for bug: _check_post_implies_spec unconditionally trusts the LLM verdict.

Bug ID: src--prompts-py--_check_post_implies_spec

Expected (spec): When the actual post-condition satisfies the specification
post-condition, returns (True, None, None, None).

Actual (bug): The function delegates the verdict entirely to an LLM and
unconditionally returns whatever the LLM says. When the LLM returns "MISMATCH"
despite identical post_condition and spec_post_condition (where the former
clearly satisfies the latter), the function incorrectly reports a violation
as (False, stmts, post_condition, reason).
"""

import json
import os
import sys
import unittest.mock as mock
from pathlib import Path

# Ensure the repo root is importable
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

# --- Save and sanitize environment to isolate the test ---
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
    # --- Step 1: Import the target function ---
    from src.prompts import _check_post_implies_spec

    # --- Step 2: Craft a fake LLM response that says MISMATCH ---
    fake_llm_response = json.dumps({
        "verdict": "MISMATCH",
        "counterexample": "x=42, y=0",
        "offending_statements": "Line 3: return x // y",
        "reason": "Hallucinated: code may divide by zero when y is 0.",
    })

    fake_usage = {"prompt_tokens": 100, "completion_tokens": 50}

    # --- Step 3: Mock _retry_create to return the fake response ---
    import src.prompts as prompts_module

    with mock.patch.object(prompts_module, "_retry_create",
                           return_value=(fake_llm_response, fake_usage)):
        has_violation, stmts, post_cond, reason = _check_post_implies_spec(
            block="def add(x, y):\n    return x + y",
            post_condition=(
                "The function returns the sum of two integers. "
                "It always succeeds and does not raise any exceptions."
            ),
            spec_post_condition=(
                "The function returns the sum of two integers. "
                "It always succeeds and does not raise any exceptions."
            ),
            knowledge="",
            language="python",
            trace_dir=None,
        )

    if has_violation is False:
        # Bug confirmed: LLM said MISMATCH but conditions are identical
        print(
            f"CONFIRMED — Function returned ({has_violation}, {stmts!r}, "
            f"{post_cond!r}, {reason!r}) instead of "
            f"(True, None, None, None). "
            f"The code unconditionally trusts an LLM MISMATCH verdict even when "
            f"post_condition and spec_post_condition are identical. "
            f"stmts={stmts!r} reason={reason!r}"
        )
    else:
        print(
            f"NOT CONFIRMED — Function correctly returned "
            f"({has_violation}, {stmts!r}, {post_cond!r}, {reason!r})"
        )

except Exception as e:
    import traceback
    traceback.print_exc()
    print(f"ERROR: {type(e).__name__}: {e}")

finally:
    # Restore environment
    for k, v in _saved_env.items():
        if v is not None:
            os.environ[k] = v
        elif k in os.environ:
            del os.environ[k]

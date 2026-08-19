"""Probe for bug: _llm_select_json propagates exceptions instead of returning None."""

import sys
import os
import tempfile
from unittest.mock import patch

# The probe is run from the repo root, so cwd is the project root directory.
# Python adds the script's own dir to sys.path, not the root. Add root explicitly.
sys.path.insert(0, os.getcwd())

# All fixtures and temp work stay in a fresh temp dir, not in fm_agent/
_workspace = tempfile.mkdtemp(prefix="probe__llm_select_json_")

passed = False
actual = None
expected = None

try:
    # Load _llm_select_json via the package entry point
    from src.incremental_reasoner import _llm_select_json

    # Patch _llm_json_call in the module where _llm_select_json looks it up.
    # In incremental_reasoner.py line 54: from .llm_client import _llm_json_call
    # So the name is bound in the incremental_reasoner module namespace.
    with patch("src.incremental_reasoner._llm_json_call") as mock_call:
        mock_call.side_effect = RuntimeError("Simulated LLM client error")

        # Per the specification, _llm_select_json must return None when the LLM
        # cannot produce valid output. A network/client exception falls under
        # "LLM produces no valid output", so the function should catch it and
        # return None — not let it propagate.
        result = _llm_select_json(
            work_dir=_workspace,
            prompt_content="test prompt",
            stage="test_stage",
            validator=lambda x: (True, x),
            schema_description="test schema",
        )

    # If we reach here without an exception, check the result.
    # The spec says a non-exceptional return should be None or valid JSON.
    # Since the mock raised, we should not be here — but we are.
    actual = result
    expected = None
    passed = False

except RuntimeError as e:
    # Bug confirmed: the exception from _llm_json_call propagated unchanged to
    # the caller. The specification requires returning None instead.
    actual = f"RuntimeError propagated: {e}"
    expected = None
    passed = True

except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)

if passed:
    print(f"CONFIRMED — exception propagated to caller (expected: None returned)")
else:
    print(f"NOT CONFIRMED — function returned {actual!r} (expected: {expected!r})")

# Cleanup temp workspace
try:
    os.rmdir(_workspace)
except OSError:
    pass

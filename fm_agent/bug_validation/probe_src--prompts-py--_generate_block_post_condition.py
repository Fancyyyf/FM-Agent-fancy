"""Probe for bug: _generate_block_post_condition does not catch exceptions from _llm_json_call.

Spec says: "Returns None when the post-condition could not be determined from the given inputs"
which implies all failure modes (including runtime errors) should be handled gracefully.
The code does `return _llm_json_call(...)` without try/except, so exceptions propagate.
"""
import sys
sys.path.insert(0, '/tmp/fm_agent_wt_FM-Agent_xyeqtgt6/snapshot')

import config  # noqa: E402, F401
import src.prompts  # noqa: E402

# Save the original function
_original_llm_json_call = src.prompts._llm_json_call


def _mock_llm_json_call(*args, **kwargs):
    """Simulate an unrecoverable LLM runtime error (e.g. network failure)."""
    raise RuntimeError("Simulated LLM API failure — network error")


try:
    # Monkey-patch _llm_json_call so _generate_block_post_condition calls our mock
    src.prompts._llm_json_call = _mock_llm_json_call

    result = src.prompts._generate_block_post_condition(
        block="x = 1",
        pre_condition="x is undefined",
        knowledge=None,
        language="python",
    )

    # If we reach here, the function returned a value instead of propagating the exception.
    # But our mock raises, so this path means the exception was caught somehow.
    print(f"NOT CONFIRMED — function returned {result!r} instead of raising | "
          f"spec requires None for undetermined post-conditions")

except Exception as exc:
    # The exception from _mock_llm_json_call propagated through _generate_block_post_condition
    # without being caught. Per spec, it should have returned None.
    print(f"CONFIRMED — exception propagated instead of returning None | "
          f"exception type: {type(exc).__name__} | message: {exc}")

finally:
    # Always restore the original function
    src.prompts._llm_json_call = _original_llm_json_call

"""Probe script for bug src--prompts-py--_generate_block_post_condition.

Spec claim: _generate_block_post_condition returns None when the post-condition
could not be determined from the given inputs.

Bug claim: The function propagates exceptions from _llm_json_call instead of
returning None. We simulate an LLM call failure by monkey-patching
_llm_json_call to raise a ValueError.

Expected (spec-correct): returns None
Actual (buggy): raises ValueError
"""

import sys

# Ensure repo root is on path for package imports
sys.path.insert(0, '.')

try:
    from src.prompts import _generate_block_post_condition
except Exception as e:
    print(f'ERROR: Failed to import module: {e}')
    sys.exit(1)


def failing_llm_json_call(*args, **kwargs):
    """Simulate an LLM call that cannot determine the post-condition."""
    raise ValueError("Simulated LLM failure: could not determine post-condition from given inputs")


# Monkey-patch _llm_json_call to simulate failure
import src.prompts as prompts_module

original = prompts_module._llm_json_call
prompts_module._llm_json_call = failing_llm_json_call

expected = None  # spec says return None when post-condition cannot be determined
actual = None
passed = False   # True means bug CONFIRMED (actual != expected)

try:
    actual = prompts_module._generate_block_post_condition(
        block="x = 1",
        pre_condition="x is uninitialized",
        knowledge="",
        language="python",
    )
    # If we reach here, the function returned instead of raising
    if actual is None:
        passed = False  # spec-compliant: returned None
    else:
        passed = True   # returned wrong value instead of None

except ValueError as e:
    # Bug CONFIRMED: raised exception instead of returning None
    actual = f"ValueError: {e}"
    passed = True

except Exception as e:
    print(f'ERROR: Unexpected exception: {e}')
    sys.exit(1)

if passed:
    print(f'CONFIRMED — actual: {actual!r} | expected: {expected!r}')
else:
    print(f'NOT CONFIRMED — actual matched expected: {actual!r}')

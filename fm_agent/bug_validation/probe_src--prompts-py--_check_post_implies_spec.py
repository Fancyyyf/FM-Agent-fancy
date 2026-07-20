import sys
import os

# Ensure the repo root is on the path so that 'src' and 'config' imports work
repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, repo_root)

from unittest.mock import patch

try:
    # Import the public API function that exercises the buggy code path
    from src.reasoner import reasoner

    # The spec says: when no definitive MATCH/MISMATCH verdict can be reached after
    # exhausting retry attempts, raises ValueError.
    # The bug: if _retry_create raises a non-ValueError exception (e.g., network error),
    # the bare `raise` on line 88 of prompts.py re-raises it as-is instead of ValueError.
    #
    # Trigger: monkey-patch _retry_create to raise RuntimeError, then call reasoner().
    # If bug exists, RuntimeError will propagate (CONFIRMED).
    # If bug is fixed, ValueError should be raised (NOT CONFIRMED).

    spec_text = (
        "Pre-condition:\n"
        "  x is a valid integer\n"
        "Post-condition:\n"
        "  returns x * 2\n"
    )
    func_text = "def double(x):\n    return x * 2\n"

    got_value_error = False
    got_other_exception = None

    with patch("src.prompts._retry_create", side_effect=RuntimeError("simulated _retry_create failure")):
        try:
            reasoner(
                func=func_text,
                spec=spec_text,
                info="",
                language="python",
            )
        except ValueError:
            got_value_error = True
        except Exception as e:
            got_other_exception = (type(e).__name__, str(e))

    if got_other_exception is not None:
        print(
            f"CONFIRMED — spec requires ValueError but got {got_other_exception[0]}: "
            f"{got_other_exception[1]}"
        )
    elif got_value_error:
        print("NOT CONFIRMED — got expected ValueError as spec requires")
    else:
        print("NOT CONFIRMED — no exception raised at all")

except Exception as e:
    print(f"ERROR: {type(e).__name__}: {e}")
    sys.exit(1)

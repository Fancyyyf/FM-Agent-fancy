"""Bug validation probe for _llm_json_call returning None instead of raising an exception.

The specification states: "When all max_retries attempts yield responses that either fail
JSON parsing or fail validator, raises an exception."

The code at src/llm_client.py line 368 returns None instead of raising.
"""

import sys
import os

# Ensure the repo root is on the path so 'from src.llm_client import ...' works
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from unittest.mock import patch


def validator_that_fails(parsed_json):
    """A validator that always rejects."""
    raise ValueError("validation failed — test probe")


def run_probe():
    """Test whether _llm_json_call raises an exception on exhaustion instead of returning None."""
    with patch("src.llm_client._retry_create") as mock_retry:
        # Return a response that parses as valid JSON so _parse_json_response succeeds,
        # but the validator will raise ValueError.
        mock_retry.return_value = ('{"key": "value"}', {"completion_tokens": 10})

        from src.llm_client import _llm_json_call

        try:
            result = _llm_json_call(
                client=None,              # mocked out by _retry_create patch
                model="test-model",
                messages=[{"role": "user", "content": "hi"}],
                validator=validator_that_fails,
                schema_description="test schema",
                max_retries=1,
                trace_dir=None,           # no trace side effects
                trace_meta=None,
            )
            # If we reach here, the function returned a value instead of raising.
            if result is None:
                print("CONFIRMED — actual: None | expected: exception (function returned None instead of raising)")
            else:
                print(f"NOT CONFIRMED — actual: {result!r} (unexpected return value)")
        except Exception as e:
            print(f"NOT CONFIRMED — function raised {type(e).__name__}: {e}")
        except SystemExit:
            raise
        except BaseException:
            raise


if __name__ == "__main__":
    try:
        run_probe()
    except Exception as exc:
        print(f"ERROR: {exc}")
        sys.exit(1)

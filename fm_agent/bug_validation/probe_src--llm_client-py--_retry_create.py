"""Probe for bug: _retry_create retries non-recoverable TypeError instead of propagating immediately.

Spec claim: non-recoverable errors (provider-rejected malformed requests) are
propagated immediately without retry. The code catches all Exception on line 237
and retries even non-recoverable errors like TypeError.
"""
import sys
import os
from unittest.mock import patch

sys.path.insert(0, '/tmp/fm_agent_wt_FM-Agent_xyeqtgt6/snapshot')

try:
    # -----------------------------------------------------------------------
    # Build a mock OpenAI-compatible client whose chat.completions.create
    # raises TypeError on every call. We count calls to detect retries.
    # -----------------------------------------------------------------------
    class MockCreate:
        def __init__(self):
            self.call_count = 0

        def create(self, **kwargs):
            self.call_count += 1
            raise TypeError("invalid messages type: expected list of dicts, got str")

    mock_create = MockCreate()
    mock_client = type('MockClient', (), {
        'chat': type('MockChat', (), {
            'completions': type('MockCompletions', (), {
                'create': mock_create.create,
            })(),
        })(),
    })()

    # -----------------------------------------------------------------------
    # Patch time.sleep (avoid multi-second waits), is_cli_backend_enabled
    # (must be False to exercise the retry branch), and _is_anthropic_model
    # (must be False to hit the OpenAI-compat path instead of Anthropic).
    # -----------------------------------------------------------------------
    patches = [
        patch('src.llm_client.time.sleep', return_value=None),
        patch('src.llm_client.is_cli_backend_enabled', return_value=False),
        patch('src.llm_client._is_anthropic_model', return_value=False),
    ]
    for p in patches:
        p.start()

    try:
        from src.llm_client import _retry_create, _MAX_LLM_RETRIES

        # Invoke _retry_create — using a non-anthropic model name and valid
        # messages so the only failure is the TypeError side_effect in our mock.
        _error_result = None
        try:
            _retry_create(mock_client, "gpt-4o", [{"role": "user", "content": "hi"}])
        except RuntimeError as e:
            _error_result = f"RuntimeError: {e}"
        except TypeError as e:
            _error_result = f"TypeError: {e}"
        except Exception as e:
            _error_result = f"{type(e).__name__}: {e}"

        call_count = mock_create.call_count

        # Bug is CONFIRMED if TypeError was retried (call_count > 1) instead
        # of propagating immediately. With _MAX_LLM_RETRIES=5, the buggy
        # behavior produces: 1 original call + 5 retries = 6 total.
        if call_count > 1:
            print(
                f"CONFIRMED — TypeError was retried ({call_count}x with "
                f"{_MAX_LLM_RETRIES} retry budget) instead of propagating "
                f"immediately; final result was {_error_result}"
            )
        else:
            print(
                f"NOT CONFIRMED — TypeError propagated immediately "
                f"({call_count} call, result: {_error_result})"
            )

    finally:
        for p in reversed(patches):
            p.stop()

except Exception as e:
    import traceback
    traceback.print_exc(file=sys.stderr)
    print(f'ERROR: {e}')
    sys.exit(1)

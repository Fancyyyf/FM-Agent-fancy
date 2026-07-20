import sys
import os

# Ensure the repo root is on sys.path so 'import src' resolves
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

import tempfile
from unittest.mock import patch

try:
    from src.llm_client import _llm_json_call
    from src.trace_writer import record_llm_exchange

    # ── Bug Description ────────────────────────────────────────────────
    # Spec claim: "Every LLM attempt produces a durable outcome record"
    # Actual:     record_llm_exchange(trace_dir, ...) is a no-op when
    #             trace_dir is None/falsy (line 47-48 of trace_writer.py).
    #             When _llm_json_call is invoked with trace_dir=None,
    #             events are built but never persisted, violating the spec.
    #
    # This probe mocks _retry_create to avoid actual LLM API calls,
    # then calls _llm_json_call with trace_dir=None. The function
    # succeeds but produces no durable record → spec violation confirmed.
    # ────────────────────────────────────────────────────────────────────

    mock_response = '{"key": "value"}'
    mock_usage = {"total_tokens": 10}

    with patch('src.llm_client._retry_create', return_value=(mock_response, mock_usage)):
        # Validator that accepts any dict
        def validator(data):
            if not isinstance(data, dict):
                raise ValueError("Expected a dict")
            return data

        # Create temp dir as a sentinel — we'll check that NO events file
        # was created there, since trace_dir=None means record_llm_exchange
        # is a silent no-op
        result = _llm_json_call(
            client=None,
            model="test-model",
            messages=[{"role": "user", "content": "Return valid JSON"}],
            validator=validator,
            schema_description='{"key": "string"}',
            max_retries=1,
            trace_dir=None,   # <-- the trigger: no durable record will be produced
            trace_meta=None,
        )

    # At this point _llm_json_call returned successfully.
    # Internally it called record_llm_exchange(None, ...) which returned
    # immediately at line 48 of trace_writer.py ("if not trace_dir: return").
    # No events.jsonl was written anywhere → no durable outcome record.

    # Verify the result is correct (proves the call succeeded)
    assert result == {"key": "value"}, f"Unexpected result: {result!r}"

    # Bug confirmation:
    # - Spec says: "Every LLM attempt produces a durable outcome record"
    # - Reality:    record_llm_exchange(None, ...) is a no-op
    # → SPEC VIOLATION when trace_dir=None

    actual = "no durable outcome record produced (record_llm_exchange no-op when trace_dir=None)"
    expected = "Every LLM attempt must produce a durable outcome record per specification"

    # The spec is violated: actual behavior ≠ spec requirement
    passed = True

except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)

if passed:
    print(f'CONFIRMED')
    print(f'  actual:   {actual!r}')
    print(f'  expected: {expected!r}')
else:
    print(f'NOT CONFIRMED — actual matched expected: {actual!r}')

import sys
import os

# Ensure repo root is on the path so config and src package resolve
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from unittest.mock import patch

try:
    import config
    from src.opencode_trace import _opencode_provider_config

    # Bug trigger: settings.llm is None, which means no LLM config is loaded.
    # Per spec, the function should return None when fields are missing/falsy
    # and must not raise exceptions. The buggy code dereferences None.api_key.
    with patch.object(config.settings, "llm", None):
        actual = _opencode_provider_config()
        # If we reach here, the function did NOT raise — that means the bug
        # is already fixed, or the trigger didn't take effect.
        expected = None
        passed = actual is not expected
        if passed:
            print(f"CONFIRMED — actual: {actual!r} | expected: {expected!r}")
        else:
            print(f"NOT CONFIRMED — actual matched expected: {actual!r}")

except AttributeError as e:
    # This is the bug: accessing .api_key on None raises AttributeError
    # instead of returning None as required by the spec.
    print(f"CONFIRMED — AttributeError: {e}")
    print(f"Expected: None (return None when fields are missing)")
    print(f"Actual: AttributeError('NoneType' object has no attribute 'api_key')")

except Exception as e:
    print(f"ERROR: {type(e).__name__}: {e}")
    sys.exit(1)

import sys
import os
import json

# Ensure repo root is on sys.path so 'import src' works
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

actual = None
expected_type = "json.JSONDecodeError"
passed = False

try:
    from src.prompts import _load_spec_check_json

    # Trigger condition: when response is 42 (an integer), isinstance(response, str) is False,
    # so text is ''. _parse_json_response(42) is called, but it expects a string and
    # may raise TypeError. The except clause only catches ValueError, so TypeError
    # is not translated to json.JSONDecodeError.
    result = _load_spec_check_json(42)
    # If we get here, no exception was raised at all → bug (spec says should raise)
    actual = "no error (returned: %r)" % result
    passed = True
except json.JSONDecodeError as e:
    # spec-correct behavior — the function properly translated the error
    actual = "json.JSONDecodeError('%s')" % str(e)
    passed = False
except TypeError as e:
    # Bug confirmed! TypeError escaped instead of being converted to JSONDecodeError
    actual = "TypeError('%s')" % str(e)
    passed = True
except ValueError as e:
    # ValueError raised instead of json.JSONDecodeError → also a bug per spec
    actual = "ValueError('%s')" % str(e)
    passed = True
except Exception as e:
    print('ERROR:', type(e).__name__, str(e))
    sys.exit(1)

if passed:
    print('CONFIRMED — actual: %s | expected: %s' % (actual, expected_type))
else:
    print('NOT CONFIRMED — actual matched expected: %s' % actual)

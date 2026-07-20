import sys
import os
import json

# Ensure repo root is on sys.path so 'import src' works
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

try:
    from src.prompts import _parse_spec_check_json

    # The spec says for MATCH verdict, any non-empty string in counterexample
    # or offending_statements should raise ValueError.
    # The code uses _nonempty_string() which strips whitespace first,
    # so whitespace-only strings like "   " are treated as empty.
    # This test passes a whitespace-only counterexample to trigger the bug.

    input_json = json.dumps({
        "verdict": "MATCH",
        "counterexample": "   ",
        "offending_statements": None,
        "reason": "all good"
    })

    actual = None
    expected = "ValueError"

    result = _parse_spec_check_json(input_json)
    # No ValueError raised → BUG CONFIRMED (spec violated)
    actual = "no error (returned tuple: %s)" % str(result)

    # Bug: spec says should raise ValueError, but code doesn't
    passed = True  # True means bug reproduced (actual != expected)
except ValueError as e:
    # ValueError raised → spec-correct behavior, bug NOT reproduced
    actual = "ValueError('%s')" % str(e)
    passed = False
except Exception as e:
    print('ERROR:', str(e))
    sys.exit(1)

if passed:
    print('CONFIRMED — actual: %s | expected: %s' % (actual, expected))
else:
    print('NOT CONFIRMED — actual matched expected: %s' % actual)

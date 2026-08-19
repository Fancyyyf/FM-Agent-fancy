"""Probe for bug: src--llm_client-py--_parse_json_response

Bug: _parse_json_response scans for '{' characters without checking whether they
appear inside a JSON string literal. A JSON object embedded in a quoted string
should not be treated as a standalone JSON value per the specification.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))

try:
    from src.llm_client import _parse_json_response
except Exception as e:
    print(f"ERROR: Cannot import _parse_json_response: {e}")
    sys.exit(1)


def main():
    try:
        # Trigger: text containing a JSON object embedded inside a quoted string.
        # The scanner finds '{' without checking if it's inside string context,
        # so it incorrectly extracts {"a": 1} from inside the string.
        test_input = 'The value is "{"a": 1}"'

        actual = _parse_json_response(test_input)

        # Bug confirmed: returned a dict instead of raising ValueError.
        # Specification requires ValueError because no standalone JSON
        # object/array exists — the braces are inside a quoted string.
        expected = "ValueError (no standalone JSON object/array)"
        print(
            f"CONFIRMED — bug reproduced: actual={actual!r} | "
            f"expected={expected!r}"
        )
    except ValueError as e:
        print(f"NOT CONFIRMED — expected ValueError raised per spec: {e}")
    except Exception as e:
        print(f"ERROR: {type(e).__name__}: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

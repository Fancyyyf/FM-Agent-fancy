"""Probe script for bug: src--generate_batch_prompts-py--extract_spec_block.

Bug: extract_spec_block() does not return None when spec keys have non-string values.
Spec requires: return None when any of signature/pre_condition/post_condition has a non-string value.
Actual: always returns formatted string using spec.get() without type-checking values.
"""

import json
import sys
import tempfile
from pathlib import Path

# Load the package via its public entry point
from src.generate_batch_prompts import extract_spec_block


def main():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)

        # Create a .spec.json with all three keys but one has a non-string value (integer)
        spec_content = {
            "signature": "my_func(int x) -> int",
            "pre_condition": 42,           # Non-string value — spec says this should cause None
            "post_condition": "returns x + 1",
        }

        test_file = tmp / "test.py"
        spec_file = tmp / "test.py.spec.json"

        spec_file.write_text(json.dumps(spec_content))

        try:
            actual = extract_spec_block(test_file)
        except Exception as e:
            print(f"ERROR: {e}", file=sys.stderr)
            sys.exit(1)

        # Spec claims: return None when any key has a non-string value
        # Actual code: returns formatted string regardless of value types
        expected = None
        passed = actual is not None  # True = bug reproduced (returned string instead of None)

        if passed:
            print(f"CONFIRMED — actual: {actual!r} | expected: {expected!r}")
            print(f"(Returned a string when spec requires None for non-string values)")
        else:
            print(f"NOT CONFIRMED — actual matched expected: {actual!r}")


if __name__ == "__main__":
    main()

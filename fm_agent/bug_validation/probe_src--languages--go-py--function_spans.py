"""Probe: Confirm that function_spans in src/languages/go.py hardcodes "go" as
the language key, causing it to return None for a non-Go file that is indexed
by the codegraph and contains top-level function definitions.

The spec claims: "Returns a list of (function_name, start_line, end_line) for
every top-level function definition found in the file at filepath." The actual
behavior only works when the file happens to be indexed as language "go".
"""

import sys
import os
from unittest.mock import MagicMock, patch

# The probe is run from the repo root, so cwd is the import base.
sys.path.insert(0, os.getcwd())


def main():
    try:
        from src.languages.go import function_spans

        proj_dir = "/fake/proj"
        # A Python file that is indexed by codegraph and contains a function
        filepath = "/fake/proj/my_script.py"

        # Create a mock CodeGraphExtractor instance
        mock_cg = MagicMock()
        # get_function_spans returns a realistic result when called with the
        # CORRECT language key ("python"), but returns None when called with
        # the hardcoded "go" key (which doesn't match the file's language).
        def mock_get_function_spans(lang_key, abs_filepath):
            if lang_key == "python":
                return [("my_func", 0, 5)]  # spec-correct result
            # lang_key == "go" → language mismatch → no rows → None
            return None

        mock_cg.get_function_spans.side_effect = mock_get_function_spans

        with patch("src.languages.go.CodeGraphExtractor.from_proj_dir",
                   return_value=mock_cg):
            actual = function_spans(proj_dir, filepath)

        # Expected: the function should return the spans for any indexed file.
        # The spec's post-condition makes no language restriction.
        expected = [("my_func", 0, 5)]

        # The bug: actual is None because "go" was hardcoded and doesn't match
        # the Python language. passed=True means the bug is reproduced.
        passed = actual != expected

        if passed:
            print(f"CONFIRMED — actual: {actual!r} | expected: {expected!r}")
            print("The hardcoded 'go' language key caused get_function_spans "
                  "to miss the python-language node, returning None instead of "
                  "the indexed function spans.")
        else:
            print(f"NOT CONFIRMED — actual matched expected: {actual!r}")

    except Exception as e:
        import traceback
        traceback.print_exc(file=sys.stderr)
        print(f"ERROR: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

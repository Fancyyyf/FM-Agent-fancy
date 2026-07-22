import sys
import os
from unittest.mock import patch, MagicMock

# The probe is run from the repo root, so cwd is the import base.
sys.path.insert(0, os.getcwd())


def main():
    try:
        from src.languages.c import function_spans

        proj_dir = "/fake/proj_dir"
        filepath = "/fake/proj_dir/empty.c"

        # Create a mock CodeGraphExtractor instance
        mock_cg = MagicMock()
        # get_function_spans returns None (simulating a file with no definitions)
        mock_cg.get_function_spans.return_value = None

        # Patch from_proj_dir to return our mock (valid codegraph, not None)
        with patch("src.languages.c.CodeGraphExtractor.from_proj_dir", return_value=mock_cg):
            actual = function_spans(proj_dir, filepath)

        # Spec: for valid codegraph, return a LIST (possibly empty), never None.
        # Bug: returns None because get_function_spans returns None for a file
        # with no definitions.
        expected = []  # spec-correct: empty list when file has no functions
        passed = actual is None  # True = bug reproduced (got None instead of [])

        if passed:
            print(f"CONFIRMED — actual: {actual!r} | expected: {expected!r}")
        else:
            print(f"NOT CONFIRMED — actual matched expected: {actual!r}")

    except Exception as e:
        import traceback
        traceback.print_exc(file=sys.stderr)
        print(f"ERROR: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

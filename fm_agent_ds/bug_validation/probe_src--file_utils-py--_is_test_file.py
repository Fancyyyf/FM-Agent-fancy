import sys
import os

# Ensure the repo root is on sys.path so 'from src.file_utils import ...' resolves
_repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

try:
    from src.file_utils import _is_test_file

    # The spec says: "Returns True when any directory component matches a recognized
    # test-directory name."  _TEST_DIR_NAMES = {"test", "tests", ...} (all lowercase).
    # The spec implies case-sensitive matching — "Tests" ∉ _TEST_DIR_NAMES.
    #
    # The code (line 262) does: `part.lower() in _TEST_DIR_NAMES`
    # So "Tests".lower() = "tests" IS in _TEST_DIR_NAMES → returns True.
    #
    # Bug: the code lowercases before checking, making the match case-insensitive.
    # Expected: False (case-sensitive does not match)
    # Actual:   True  (code lowercases, producing case-insensitive match)

    test_path = "a/Tests/file.py"

    actual = _is_test_file(test_path)
    expected = False  # per spec — case-sensitive: "Tests" not in {"tests", ...}

    bug_reproduced = actual != expected

    if bug_reproduced:
        print(f"CONFIRMED — actual: {actual!r} | expected: {expected!r}")
    else:
        print(f"NOT CONFIRMED — actual matched expected: {actual!r}")

except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)

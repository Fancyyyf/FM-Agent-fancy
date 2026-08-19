import sys
import os

# Ensure the repo root is on sys.path so 'from src.file_utils import ...' resolves
_repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

try:
    from src.file_utils import _is_test_file, add_test_file_exemption, clear_test_file_exemptions

    # Clear any prior state
    clear_test_file_exemptions()

    # Scenario: entry_func lives in a test directory (e.g. tests/entry_main.py).
    # A callee function bar is also in a test directory (tests/test_helpers.py).
    # run_entry_pipeline calls add_test_file_exemption() for the entry file only.
    # The callee's file is never exempted, so bar's functions are silently skipped.
    entry_file = "tests/entry_main.py"
    helper_file = "tests/test_helpers.py"

    # Both files reside under tests/ which is in _TEST_DIR_NAMES.
    entry_is_test_before = _is_test_file(entry_file)
    helper_is_test_before = _is_test_file(helper_file)

    # Simulate run_entry_pipeline: exempt ONLY the entry_func's source file.
    add_test_file_exemption(entry_file)

    # After the exemption:
    entry_is_test_after = _is_test_file(entry_file)
    helper_is_test_after = _is_test_file(helper_file)

    # The spec requires ALL functions reachable from entry_func to be processed.
    # The code only exempts the entry file; other reachable functions in test
    # files remain classified as test files and are skipped.
    gap_exists = (
        entry_is_test_before
        and helper_is_test_before
        and (not entry_is_test_after)
        and helper_is_test_after
    )

    # Cleanup
    clear_test_file_exemptions()

    if gap_exists:
        print(
            f"CONFIRMED — run_entry_pipeline exempts only entry_func's source file "
            f"({entry_file}); other reachable functions in {helper_file} remain "
            f"classified as test files and are silently skipped"
        )
    else:
        print(
            f"NOT CONFIRMED — entry_before={entry_is_test_before!r}, "
            f"helper_before={helper_is_test_before!r}, "
            f"entry_after={entry_is_test_after!r}, "
            f"helper_after={helper_is_test_after!r}"
        )

except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)

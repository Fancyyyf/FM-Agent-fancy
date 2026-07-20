import sys

try:
    from src.file_utils import add_test_file_exemption, clear_test_file_exemptions
    import src.file_utils as futils

    # Add some exemptions to populate the set
    add_test_file_exemption("path/to/test1.py")
    add_test_file_exemption("path/to/test2.py")
    add_test_file_exemption("some/other/test.py")

    # Verify set is non-empty before calling clear
    before = set(futils._TEST_FILE_EXEMPTIONS)
    if not before:
        print('SETUP FAILED — _TEST_FILE_EXEMPTIONS was already empty before clear')
        sys.exit(1)

    # Call clear
    clear_test_file_exemptions()

    after = futils._TEST_FILE_EXEMPTIONS

    # According to spec: set should be empty
    # If it IS empty, the spec is satisfied (NOT CONFIRMED = bug not reproducible)
    # If NOT empty, the bug is confirmed
    if len(after) > 0:
        print(f'CONFIRMED — actual: {after!r} (not empty) | expected: set() (empty)')
    else:
        print(f'NOT CONFIRMED — actual matched expected: {before!r} -> {after!r} (empty after clear)')

except Exception as e:
    import traceback
    traceback.print_exc()
    print(f'ERROR: {e}')
    sys.exit(1)

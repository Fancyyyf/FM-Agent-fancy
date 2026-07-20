# [SPEC]
# Unit: fm_agent/extracted_functions/src/file_utils-py/clear_test_file_exemptions.py
#
# clear_test_file_exemptions()
#
# Pre-condition:
#   - The module-level set `_TEST_FILE_EXEMPTIONS` exists.
#
# Post-condition:
#   - The module-level set of exempted test-file paths is empty.
#   - All paths previously registered via `add_test_file_exemption` are no longer
#     exempt; subsequent test-file classification functions will apply default
#     heuristics to every path.
# [SPEC]

# [INFO]
# (no callees)
# [INFO]

def clear_test_file_exemptions():
    """Drop all registered test-file exemptions."""
    _TEST_FILE_EXEMPTIONS.clear()

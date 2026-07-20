# [SPEC]
# Unit: fm_agent/extracted_functions/src/file_utils-py/add_test_file_exemption.py
#
# add_test_file_exemption(rel_path)
#
# Pre-condition:
#   - rel_path is a string representing a file path.
#
# Post-condition:
#   - The module-level set of exempted test-file paths contains a normalized form of
#     rel_path where every backslash ('\\') is replaced by a forward slash ('/').
#   - A subsequent invocation of any test-file classification function will exclude
#     this normalized path from classification as a test file.
# [SPEC]

# [INFO]
# (no callees)
# [INFO]

def add_test_file_exemption(rel_path):
    """Exempt a project-relative source path from the test-file heuristics."""
    _TEST_FILE_EXEMPTIONS.add(rel_path.replace('\\', '/'))

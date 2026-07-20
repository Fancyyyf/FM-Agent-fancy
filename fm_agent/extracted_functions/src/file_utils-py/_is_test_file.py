# [SPEC]
# Unit: src/file_utils-py/_is_test_file.py
#
# _is_test_file(rel_path) -> bool
#
# Pre-condition:
#   - rel_path is a non-empty string representing a relative file path
#
# Post-condition:
#   - Returns True when rel_path identifies a file classified by the module as a test file
#   - Returns False when rel_path is not classified as a test file
#   - A path explicitly listed in the module-level test-file exemption set is never classified as a test file
#   - A path is classified as a test file when any directory component (path segments excluding the filename)
#     matches the module-level test-directory naming rules
#   - A path is classified as a test file when its filename matches any of the module-level compiled
#     test-filename regex patterns
#   - Test-directory matching is case-insensitive; test-filename matching follows the compiled regex rules
#   - The function normalizes platform path separators to forward slashes before classification
# [SPEC]

# [INFO]
# (no callees)
# [INFO]

def _is_test_file(rel_path):
    """Return True if the relative source path looks like a test file."""
    norm_path = rel_path.replace('\\', '/')
    if norm_path in _TEST_FILE_EXEMPTIONS:
        return False
    parts = norm_path.split('/')
    # Check if any directory component is a known test directory
    for part in parts[:-1]:
        if part.lower() in _TEST_DIR_NAMES:
            return True
    # Check filename against test patterns
    basename = parts[-1]
    for pat in _TEST_FILE_PATTERNS:
        if pat.match(basename):
            return True
    return False

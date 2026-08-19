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

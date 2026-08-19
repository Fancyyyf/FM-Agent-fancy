def add_test_file_exemption(rel_path):
    """Exempt a project-relative source path from the test-file heuristics."""
    _TEST_FILE_EXEMPTIONS.add(rel_path.replace('\\', '/'))

def _enumerate_source_files(proj_dir):
    """List every supported, non-test source file under proj_dir (relative paths).

    Skips the fm_agent/ and .git/ directories and applies the same language and
    test-file filters run_extraction uses, so the returned files are exactly the
    ones that will yield extracted functions. The entry_func's source file is
    still included when it looks like a test, because run_entry_pipeline
    registers it as a test-file exemption before selection runs.
    """
    source_files = []
    for root, dirs, files in os.walk(proj_dir):
        dirs[:] = [d for d in dirs if d not in ("fm_agent", ".git")]
        for fname in files:
            src_rel = os.path.relpath(os.path.join(root, fname), proj_dir).replace(os.sep, "/")
            ext = fname.rsplit(".", 1)[-1] if "." in fname else ""
            if EXT_TO_LANG.get(ext) and not _is_test_file(src_rel):
                source_files.append(src_rel)
    return sorted(source_files)

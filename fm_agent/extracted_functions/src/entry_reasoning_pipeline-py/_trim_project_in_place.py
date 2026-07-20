# [SPEC]
# Unit: fm_agent/extracted_functions/src/entry_reasoning_pipeline-py/_trim_project_in_place.py
#
# _trim_project_in_place(proj_dir, all_by_source, keep_by_source) -> None
#
# Pre-condition:
#   - proj_dir is an absolute or relative path to an existing directory
#   - all_by_source is a dict mapping source-file relative paths (str) to a non-empty set of all function names (str) that were extracted from that file
#   - keep_by_source is a dict mapping source-file relative paths (str) to a non-empty set of function names (str) selected to preserve
#   - Every key in both dicts uses "/" as the path separator
#   - Every source_rel in keep_by_source is also a key in all_by_source
#
# Post-condition:
#   - For each source_rel in all_by_source where the source file does not exist under proj_dir, no mutation occurs for that entry
#   - For each source_rel in all_by_source where the source file exists under proj_dir and source_rel is absent from keep_by_source (or its mapped value produces an empty set), the source file is deleted from proj_dir
#   - For each source_rel in all_by_source where the source file exists under proj_dir and source_rel maps to a non-empty set of function names in keep_by_source, the source file at proj_dir/source_rel is rewritten such that every function body whose name is in all_by_source[source_rel] but not in keep_by_source[source_rel] is removed, while all lines not belonging to a function body (comments, imports, top-level statements) are preserved in their original form
#   - No source file whose relative path is absent from all_by_source is modified or deleted
#   - A single-line summary message is printed to stdout containing the total count of function bodies preserved, the total count of function bodies removed, and the total count of source files deleted
# [SPEC]

# [INFO]
# _trim_source_file(src_path, keep_names, proj_dir) -> (kept: int, removed: int)
#   Pre-condition: src_path is an absolute path to an existing source file; keep_names is a non-empty collection of function names to preserve; proj_dir is the project root directory
#   Post-condition: The file at src_path is rewritten such that every function body whose name is not a member of keep_names is removed, while all lines not belonging to a function body are preserved in their original form; the source file remains at the same path; returns a tuple (kept, removed) where kept is the count of function bodies preserved and removed is the count of function bodies removed, both non-negative integers whose sum equals the original number of function bodies in the file
# [INFO]

def _trim_project_in_place(proj_dir, all_by_source, keep_by_source):
    """Delete the unselected functions and source files from proj_dir.

    Source files with at least one selected function are trimmed to keep only
    the selected function bodies (plus all non-function context lines); source
    files whose functions are all unselected are deleted outright. Files that
    contributed no extracted functions (configs, docs, unsupported languages,
    test files) are left untouched.
    """
    total_kept = total_removed = deleted_files = 0
    for source_rel in sorted(all_by_source):
        src_path = os.path.join(proj_dir, source_rel)
        if not os.path.isfile(src_path):
            continue
        keep_names = keep_by_source.get(source_rel)
        if not keep_names:
            os.remove(src_path)
            deleted_files += 1
            continue
        kept, removed = _trim_source_file(src_path, keep_names, proj_dir)
        total_kept += kept
        total_removed += removed

    print(
        f"[EntryPipeline] Trimmed {proj_dir}: kept {total_kept} function(s), "
        f"removed {total_removed} function(s), deleted {deleted_files} source file(s)."
    )

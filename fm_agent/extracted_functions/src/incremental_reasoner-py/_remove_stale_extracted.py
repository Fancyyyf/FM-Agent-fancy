# [SPEC]
# _remove_stale_extracted(proj_dir, modified_functions) -> None
#
# Pre-condition:
#   - proj_dir is an absolute path to the project root directory, under which the child directory fm_agent/ exists with sub-directory extracted_functions/ and a phases.json file.
#   - modified_functions is a dict whose keys are absolute source-file paths (the values are not used by this function).
#
# Post-condition:
#   - For every absolute source-file path that is either a key in modified_functions or listed in the "source_files" entries of all phases loaded from phases.json, the extracted-function tree under fm_agent/extracted_functions/ associated with that source file is reconciled with the current codegraph output. Any extracted function file or directory that no longer corresponds to a current source function (including when the source file itself is absent) is deleted, and any empty parent directories are pruned.
#   - Files and directories under fm_agent/extracted_functions/ that correspond to source files not in the union of modified_functions keys and phases.json entries are unchanged.
# [SPEC]

# [INFO]
# _load_phases(fm_agent_dir: str) -> dict
#   Pre-condition: fm_agent_dir is a directory path containing a phases.json file.
#   Post-condition: Reads and returns the parsed contents of phases.json as a dict. The dict has a key "phases" whose value is a list of phase objects; each phase object contains a key "modules" (list of module objects), and each module object contains a key "source_files" (list of relative source-file paths). May raise OSError, ValueError, or KeyError on failure.
# _reconcile_extracted_dir(proj_dir: str, abs_src: str) -> None
#   Pre-condition: proj_dir is the absolute project root; abs_src is an absolute source-file path within proj_dir (the file may or may not exist).
#   Post-condition: Determines the extracted-functions directory for abs_src using the same naming convention as run_extraction. If that directory does not exist, no changes are made. Otherwise, expected extracted files are derived from the current function spans of abs_src, using the same backend (codegraph or regex) as run_extraction. If abs_src does not exist or its extension is not recognized, the expected set is empty. Any file in the directory not matching an expected path is deleted, and empty subdirectories are pruned. Expected files are preserved unchanged.
# [INFO]

def _remove_stale_extracted(proj_dir, modified_functions):
    """
    Reconcile the extracted-function tree against what codegraph now produces,
    deleting any file that no longer corresponds to a current source function and
    pruning emptied directories.

    We reconcile every source file in the current phases.json plus any file
    reported changed or deleted — not only files whose regex-visible function names
    changed. A qualifier-only edit (e.g. renaming a C++ namespace around an
    otherwise identical ``void foo(){...}``) moves the extracted file to a new
    qualified directory without changing the regex name or body, so the old
    qualified file would otherwise linger as a stale, orphaned spec. Reconciling by
    path rather than by (class-less) name handles it.
    """
    srcs = set(modified_functions)  # abs paths; includes deleted source files
    try:
        phases_data = _load_phases(os.path.join(proj_dir, "fm_agent"))
        for phase in phases_data.get("phases", []):
            for module in phase.get("modules", []):
                for rel in module.get("source_files", []):
                    srcs.add(os.path.abspath(os.path.join(proj_dir, rel)))
    except (OSError, ValueError, KeyError):
        pass
    for abs_src in srcs:
        _reconcile_extracted_dir(proj_dir, abs_src)

# [SPEC]
# Unit: src/incremental_reasoner.py
#
# check_last_run_existence(proj_dir, submodules=None) -> bool
#
# Pre-condition:
#   - proj_dir is a path to a project directory for which run_pipeline has been
#     previously executed (or attempted).
#   - submodules is None or a non-empty list of project-relative directory paths
#     using "/" separators.
#
# Post-condition:
#   - Returns True if and only if, under proj_dir/fm_agent/, all of the following
#     hold simultaneously:
#       1. The file phases.json exists.
#       2. The directory extracted_functions/ exists and contains at least one
#          function file within the scope determined by submodules.
#       3. Every function file in extracted_functions/ that falls within the
#          submodules scope carries both [SPEC] and [INFO] markers (as determined
#          by is_file_ready).
#   - Returns False when any of the three conditions above fails, including:
#       * phases.json does not exist.
#       * extracted_functions/ does not exist.
#       * No function file exists within the selected scope.
#       * At least one function file within the selected scope exists but lacks
#         [SPEC] and/or [INFO] markers.
#   - When submodules is None, the scope is the entire extracted_functions/
#     directory (all function files are considered).
#   - The function does not raise exceptions under normal file-system conditions.
# [SPEC]

# [INFO]
# _is_under_submodules(rel_path, submodules) -> bool
#   Pre-condition: rel_path is a "/"-separated relative path; submodules is a
#     non-empty list of "/"-separated directory prefix strings.
#   Post-condition: Returns True when rel_path has one of the submodules entries
#     as a prefix (i.e., rel_path starts with some prefix from submodules);
#     otherwise returns False.
# [SPLIT]
# is_file_ready(filepath) -> bool
#   Pre-condition: filepath is an absolute path to an extracted function file.
#   Post-condition: Returns True when the file contains at least two [SPEC]
#     markers and at least two [INFO] markers; otherwise returns False.
# [INFO]

def check_last_run_existence(proj_dir, submodules=None):
    """
    Return whether a full pipeline run (run_pipeline) has already completed under proj_dir.

    Incremental analysis compares the current working tree against the artifacts left by a
    previous full run, so it can only proceed when those artifacts are present. A full run
    is considered to exist when, under proj_dir/fm_agent/, both:

      1. phases.json exists — the module/phase plan that the full run aborts without, and
      2. extracted_functions/ holds at least one function file and EVERY function file
         there is specced (carries the [SPEC]/[INFO] blocks, per is_file_ready) — proving
         the spec-generation stage ran to completion. A partially specced tree means the
         previous full run did not finish, so it is not a sound basis for incremental
         analysis.

    When submodules is provided, only extracted functions under those selected
    project-relative directories are considered. Returns True only when the
    selected scope has at least one ready function and no selected function is
    incomplete; otherwise False (so the caller can fall back to a scoped full run).
    """
    work_dir = os.path.join(proj_dir, "fm_agent")

    if not os.path.isfile(os.path.join(work_dir, "phases.json")):
        return False

    extracted_dir = os.path.join(work_dir, "extracted_functions")
    if not os.path.isdir(extracted_dir):
        return False

    saw_function = False
    for root, _, files in os.walk(extracted_dir):
        for fname in files:
            fpath = os.path.join(root, fname)
            rel = os.path.relpath(fpath, extracted_dir).replace(os.sep, "/")
            if submodules and not _is_under_submodules(rel, submodules):
                continue
            saw_function = True
            if not is_file_ready(fpath):
                return False
    return saw_function

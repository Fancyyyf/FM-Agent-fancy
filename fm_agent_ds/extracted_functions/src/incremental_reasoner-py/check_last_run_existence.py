def check_last_run_existence(proj_dir, submodules=None):
    """
    Return whether a full pipeline run (run_pipeline) has already completed under proj_dir.

    Incremental analysis compares the current working tree against the artifacts left by a
    previous full run, so it can only proceed when those artifacts are present. A full run
    is considered to exist when, under proj_dir/fm_agent/, both:

      1. phases.json exists — the module/phase plan that the full run aborts without, and
      2. extracted_functions/ holds at least one function file and EVERY function file
         has both metadata sidecars (per is_file_ready) — proving
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
            if _is_metadata_sidecar(fpath):
                continue
            rel = os.path.relpath(fpath, extracted_dir).replace(os.sep, "/")
            if submodules and not _is_under_submodules(rel, submodules):
                continue
            saw_function = True
            if not is_file_ready(fpath):
                return False
    return saw_function

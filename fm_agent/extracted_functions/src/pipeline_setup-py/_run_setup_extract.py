# [SPEC]
# Unit: src/pipeline_setup-py/_run_setup_extract.py
#
# _run_setup_extract(proj_dir, work_dir, script_dir, is_incremental=False, resume=False, required_source_files=None, submodules=None, one_phase=False) -> None
#
# Pre-condition:
#   - proj_dir is a valid path to the project root directory containing source code.
#   - work_dir is a writable directory path for fm_agent workspace outputs.
#   - script_dir is a valid path to the directory containing pipeline scripts.
#
# Post-condition:
#   - Executes the setup pipeline sub-stages in order: phase generation, post-processing, and domain-context generation.
#   - When resume is True and phases.json was not modified by post-processing, domain-context generation is skipped and existing domain context files are reused.
#   - After all sub-stages complete, verifies that phases.json, engine_overview.txt, and at least one phase_NN_types.txt exist under work_dir.
#   - If the verification step finds any required output missing, prints an error message to stdout listing the expected outputs and terminates the process via sys.exit(1).
#   - Does not return if setup outputs are incomplete; otherwise returns normally.
# [SPEC]

# [INFO]
# _run_generate_phases(proj_dir, work_dir, script_dir, is_incremental, resume, submodules) -> None
#   Pre-condition: proj_dir, work_dir, and script_dir are valid paths. The flags is_incremental, resume, and submodules control behavior.
#   Post-condition: Either phases.json exists in work_dir, or the process has terminated via sys.exit(1).
# [SPLIT]
# _post_process_phases(proj_dir, work_dir, required_source_files, submodules, one_phase=False) -> bool
#   Pre-condition: phases.json exists in work_dir.
#   Post-condition: Returns True if phases.json was structurally modified (files added, removed, or reassigned across phases, phases renumbered, or empty phases cleaned); returns False if phases.json was unchanged.
# [SPLIT]
# _run_generate_domain_context(proj_dir, work_dir, script_dir, resume=False) -> None
#   Pre-condition: phases.json exists in work_dir.
#   Post-condition: Either engine_overview.txt and one phase_NN_types.txt per phase exist in work_dir, or the process has terminated via sys.exit(1).
# [SPLIT]
# _setup_outputs_complete(work_dir) -> bool
#   Pre-condition: work_dir is a valid directory that may contain pipeline outputs.
#   Post-condition: Returns True if phases.json, engine_overview.txt, and at least one phase_NN_types.txt all exist under work_dir; returns False otherwise.
# [INFO]

def _run_setup_extract(proj_dir, work_dir, script_dir, is_incremental=False,
                       resume=False, required_source_files=None,
                       submodules=None, one_phase=False):
    """Run generate-phases, post-process, and generate-domain-context stages.

    Backward-compatible wrapper that calls the three sub-stages in sequence.
    """
    _run_generate_phases(proj_dir, work_dir, script_dir, is_incremental, resume, submodules)
    phases_modified = _post_process_phases(proj_dir, work_dir, required_source_files, submodules, one_phase=one_phase)
    _run_generate_domain_context(proj_dir, work_dir, script_dir, resume and not phases_modified)

    if not _setup_outputs_complete(work_dir):
        print(
            "[Pipeline] ERROR: Stage 1/2 outputs are incomplete after "
            "post-processing. Expected fm_agent/phases.json, "
            "fm_agent/spec_prompts/domain_context/engine_overview.txt, and one "
            "phase_NN_types.txt per phase."
        )
        sys.exit(1)

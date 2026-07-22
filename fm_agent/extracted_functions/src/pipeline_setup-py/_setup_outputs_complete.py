# [SPEC]
# Unit: src/pipeline_setup-py/_setup_outputs_complete.py
#
# _setup_outputs_complete(work_dir) -> bool
#
# Pre-condition:
#   - work_dir is a valid directory path that may or may not contain pipeline output files.
#
# Post-condition:
#   - Returns True when phases.json, engine_overview.txt, and at least one file whose name matches the pattern phase_NN_types.txt (where NN is one or more digits) all exist as regular files under work_dir.
#   - Returns False when any one of the three required output categories is absent from work_dir.
# [SPEC]

# [INFO]
# _phase_plan_complete(work_dir) -> bool
#   Pre-condition: work_dir is a string path to an existing directory.
#   Post-condition: Returns True if phases.json exists as a regular file under work_dir, its content parses as valid JSON, and it conforms to the required schema; returns False otherwise.
# [SPLIT]
# _domain_context_complete(work_dir) -> bool
#   Pre-condition: work_dir is a valid directory path.
#   Post-condition: Returns True if engine_overview.txt and at least one file matching the pattern phase_NN_types.txt (where NN is one or more digits) both exist as regular files under work_dir; returns False otherwise.
# [INFO]

def _setup_outputs_complete(work_dir):
    """Return True when both phase plan and domain context are complete."""
    return _phase_plan_complete(work_dir) and _domain_context_complete(work_dir)

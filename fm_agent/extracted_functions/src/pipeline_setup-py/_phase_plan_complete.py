# [SPEC]
# Unit: src/pipeline_setup-py/_phase_plan_complete.py
#
# _phase_plan_complete(work_dir) -> bool
#
# Pre-condition:
#   - work_dir is a string path to an existing directory.
#
# Post-condition:
#   - Returns True when the file phases.json exists under work_dir, is a
#     regular file, and parses as valid JSON.
#   - Returns False when phases.json does not exist under work_dir, is not a
#     regular file, or exists but does not parse as valid JSON.
#   - The return value is idempotent for the same filesystem state: repeated
#     calls with the same work_dir and same phases.json content return the same
#     boolean.
# [SPEC]

# [INFO]
# _json_file_is_valid(file_path) -> bool
#   Pre-condition: file_path is a string path.
#   Post-condition: Returns True when the file at file_path exists, is a
#     regular file, and its content parses as valid JSON; returns False when
#     the file does not exist, is not a regular file, or its content does not
#     parse as valid JSON.
# [INFO]

def _phase_plan_complete(work_dir):
    """Return True only if phases.json exists and is valid JSON."""
    phases_path = os.path.join(work_dir, "phases.json")
    return _json_file_is_valid(phases_path)

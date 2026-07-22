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
#     regular file, its content parses as valid JSON, and it conforms to the
#     required schema (as determined by _phase_plan_schema_errors).
#   - Returns False when phases.json does not exist under work_dir, is not a
#     regular file, does not parse as valid JSON, or does not conform to the
#     required schema.
#   - The return value is idempotent for the same filesystem state: repeated
#     calls with the same work_dir and same file content yield the same boolean
#     result.
# [SPEC]

# [INFO]
# _phase_plan_schema_errors(file_path) -> any
#   Pre-condition: file_path is a string path to a file.
#   Post-condition: Returns a truthy value (a non-empty list of error strings)
#     if the file cannot be read (any OS error including absent file or
#     permission denied), if the file content is not valid JSON, or if the
#     decoded JSON violates the required schema.
#   - Returns a falsey value (an empty list) when the file is readable, its
#     content is valid JSON, and the decoded JSON fully conforms to the
#     required schema.
# [INFO]

def _phase_plan_complete(work_dir):
    """Return True only if phases.json exists and matches the required schema."""
    phases_path = os.path.join(work_dir, "phases.json")
    return not _phase_plan_schema_errors(phases_path)

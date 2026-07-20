# [SPEC]
# Unit: src/pipeline_setup-py/_domain_context_complete.py
#
# _domain_context_complete(work_dir) -> bool
#
# Pre-condition:
#   - work_dir is a valid directory path
#
# Post-condition:
#   - Returns True if and only if all of the following hold simultaneously:
#     (a) phases.json exists under work_dir and is a well-formed JSON file
#         containing a "phases" array
#     (b) spec_prompts/domain_context/engine_overview.txt exists as a regular
#         file under work_dir
#     (c) For every phase object in phases.json whose "phase" key is a numeric
#         value, the file spec_prompts/domain_context/phase_NN_types.txt
#         (where NN is the phase number zero-padded to 2 digits) exists as a
#         regular file under work_dir
#     (d) No phase object in phases.json has a missing or non-numeric "phase"
#         key
#   - Returns False when any of conditions (a)-(d) is not satisfied
#   - Does not modify any filesystem state: the function performs only
#     existence checks and reads, never creates, updates, or deletes files
# [SPEC]

# [INFO]
# _json_file_is_valid(path) -> bool
#   Pre-condition: path is a string
#   Post-condition: Returns True if and only if path refers to an existing
#                    regular file whose contents are successfully parseable as
#                    JSON; returns False when path does not exist, is not a
#                    regular file, or its contents cannot be parsed as JSON
# [INFO]

def _domain_context_complete(work_dir):
    """Return True only if all domain context files exist and match the phases in phases.json."""
    phases_path = os.path.join(work_dir, "phases.json")
    if not _json_file_is_valid(phases_path):
        return False

    domain_dir = os.path.join(work_dir, "spec_prompts", "domain_context")
    if not os.path.exists(os.path.join(domain_dir, "engine_overview.txt")):
        return False

    try:
        with open(phases_path, "r") as f:
            phases_data = json.load(f)
    except (OSError, json.JSONDecodeError):
        return False

    for phase in phases_data.get("phases", []):
        phase_num = phase.get("phase")
        if phase_num is None:
            return False
        types_path = os.path.join(domain_dir, f"phase_{phase_num:02d}_types.txt")
        if not os.path.exists(types_path):
            return False

    return True

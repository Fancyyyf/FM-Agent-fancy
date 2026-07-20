# [SPEC]
# Unit: src/file_utils-py/_get_all_phase_files.py
#
# _get_all_phase_files(phases_data, input_dir) -> list[str]
#
# Pre-condition:
#   - phases_data is a dict conforming to the phases.json schema: it has a "phases" key
#     whose value is a list of phase info dicts, each containing at least a "phase" field
#     (integer phase number).
#   - input_dir is an existing directory path under which extracted function files are stored.
#
# Post-condition:
#   - Returns a list of relative file paths, each identifying an extracted function file
#     that is reachable from at least one phase in phases_data.
#   - The returned list is deduplicated: each relative path appears at most once.
#   - The order of paths in the returned list follows the first occurrence encountered
#     when iterating phases_data["phases"] in the given order.
#   - Phases whose phase_info dict lacks a "phase" key or whose "phase" value is None
#     are silently skipped and contribute no files to the result.
#   - The return value may be an empty list when phases_data contains no phases or when
#     no extracted function files are reachable from any phase.
# [SPEC]

# [INFO]
# _get_phase_files(phases_data, phase_num, input_dir) -> iterable[str]
#   Pre-condition:
#     - phases_data is a dict conforming to the phases.json schema.
#     - phase_num is an integer identifying a valid phase within phases_data.
#     - input_dir is an existing directory path.
#   Post-condition:
#     - Returns an iterable of relative file paths of extracted function files that
#       belong to the specified phase.
#     - Each returned path corresponds to a function declared in the source files
#       assigned to phase phase_num in phases_data.
# [INFO]

def _get_all_phase_files(phases_data, input_dir):
    """Return extracted function files reachable from all phases in phases.json."""
    phase_files = []
    seen = set()
    for phase_info in phases_data.get("phases", []):
        phase_num = phase_info.get("phase")
        if phase_num is None:
            continue
        for rel in _get_phase_files(phases_data, phase_num, input_dir):
            if rel not in seen:
                seen.add(rel)
                phase_files.append(rel)
    return phase_files

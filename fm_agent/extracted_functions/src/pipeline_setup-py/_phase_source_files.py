# [SPEC]
# Unit: src/pipeline_setup.py
#
# _phase_source_files(phases_json) -> dict[int, list[str]]
#
# Pre-condition:
#   - phases_json is a string path to a phases.json file whose schema
#     conforms to the phases.json specification: a JSON object with a
#     "phases" key containing an array of phase objects, each with a
#     "phase" key (integer) and a "modules" key (array of module objects,
#     each with a "source_files" key containing an array of string paths).
#
# Post-condition:
#   - When phases_json cannot be read (file missing, unreadable) or contains
#     invalid JSON, returns an empty dict.
#   - Otherwise returns a dict[int, list[str]] mapping each phase number
#     present in the file to the concatenation of all source_files arrays
#     from ALL modules within that phase. Phases whose "phase" key is
#     absent or null are silently skipped.
#   - The returned dict may contain entries whose value is an empty list
#     if the corresponding phase has modules but no source files.
#   - Each source file path in the returned lists is a string exactly as it
#     appears in phases.json (no normalization, no resolution).
# [SPEC]

# [INFO]
# (no callees)
# [INFO]

def _phase_source_files(phases_json):
    """Return a mapping of phase number -> its combined source files in phases.json.

    Files from all of a phase's modules are merged, so an empty list means the
    phase currently owns no source files. A missing or malformed phases.json yields
    an empty mapping.
    """
    try:
        with open(phases_json, "r") as f:
            data = json.load(f)
    except (OSError, ValueError):
        return {}
    result = {}
    for phase in data.get("phases", []):
        phase_num = phase.get("phase")
        if phase_num is None:
            continue
        files = result.setdefault(phase_num, [])
        for module in phase.get("modules", []):
            files.extend(module.get("source_files", []))
    return result

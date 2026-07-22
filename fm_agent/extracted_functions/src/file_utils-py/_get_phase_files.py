# [SPEC]
# Unit: src/file_utils-py/_get_phase_files.py
#
# _get_phase_files(phases_data, phase_num, input_dir) -> list[str]
#
# Pre-condition:
#   - phases_data is a dict conforming to the phases.json schema: it has a "phases" key
#     whose value is a list of phase info dicts, each containing at least a "phase" field
#     (integer phase number) and a "modules" field.
#   - phase_num is an integer that matches the "phase" field of exactly one dict in
#     phases_data["phases"]. If no phase dict has a matching "phase" field, StopIteration
#     is raised.
#   - Each module dict in the matched phase has a "source_files" key whose value is an
#     iterable of string paths using "/" separators.
#   - input_dir is an existing directory path under which extracted function files are
#     stored following the engine directory-layout convention.
#
# Post-condition:
#   - Returns a list of relative path strings, each being the path from input_dir to a
#     regular file located under an extracted-function subdirectory.
#   - Each returned path originates from a source file declared in the modules of the
#     phase identified by phase_num; the mapping from a source file path to its
#     extracted-function subdirectory follows the engine convention: the last "." in the
#     source file's basename is replaced by "-", and the resulting name is used as a
#     subdirectory under input_dir joined with the source file's directory portion.
#   - Source files whose corresponding extracted-function subdirectory does not exist
#     under input_dir contribute no entries to the result (they are silently skipped).
#   - Within each extracted-function subdirectory, contained regular files appear in
#     lexicographically sorted order by filename.
#   - The overall order of paths in the result preserves: the iteration order of
#     phases_data["phases"], the iteration order of modules within the matched phase,
#     and the iteration order of source_files within each module.
#   - The returned list may be empty when the matched phase has no modules, no source
#     files, or none of its source files have an existing extracted-function directory.
# [SPEC]

# [INFO]
# (no callees)
# [INFO]

def _get_phase_files(phases_data, phase_num, input_dir):
    """Return relative paths of extracted function files for a given phase."""
    phase = next(p for p in phases_data["phases"] if p["phase"] == phase_num)
    phase_files = []
    for module in phase["modules"]:
        for src_file in module["source_files"]:
            dir_part = os.path.dirname(src_file)
            base = os.path.basename(src_file)
            dot_idx = base.rfind(".")
            if dot_idx >= 0:
                subdir = base[:dot_idx] + "-" + base[dot_idx + 1:]
            else:
                subdir = base
            extracted_dir = os.path.join(input_dir, dir_part, subdir)
            if os.path.isdir(extracted_dir):
                # Every extracted function is a flat file directly in
                # extracted_dir, member functions keeping the class qualifier in
                # the name (<file>-cpp/LocalStorage::Flush.cpp). os.walk stays
                # robust to any legacy nested file.
                for root, _dirs, fnames in os.walk(extracted_dir):
                    for fname in sorted(fnames):
                        fpath = os.path.join(root, fname)
                        if os.path.isfile(fpath):
                            phase_files.append(os.path.relpath(fpath, input_dir))
    return phase_files

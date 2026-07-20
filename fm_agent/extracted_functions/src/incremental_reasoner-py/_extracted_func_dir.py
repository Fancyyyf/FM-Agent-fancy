# [SPEC]
# Unit: fm_agent/extracted_functions/src/incremental_reasoner-py/_extracted_func_dir.py
#
# _extracted_func_dir(extracted_base, src_rel) -> str
#
# Pre-condition:
#   - extracted_base is a non-empty string path to the extracted_functions directory
#   - src_rel is a non-empty string representing a source file path relative to the
#     project root, using forward slash separators, following the phases.json convention
#
# Post-condition:
#   - Returns the absolute directory path where extracted-function files for the source
#     file identified by src_rel are (or would be) stored, following the naming convention
#     that mirrors the extraction mapping
#   - The returned path is formed by joining extracted_base, the directory portion of
#     src_rel (if any), and a directory name derived from the basename of src_rel
#   - The directory name derivation rule: the last dot in the source file basename is
#     replaced with a hyphen; if the basename contains no dot, it is used as-is
#   - Example: for src_rel = "src/engine/loader.cpp" and extracted_base pointing to
#     extracted_functions/, the returned path ends with "src/engine/loader-cpp"
#   - The returned path uses the platform-native path separator
# [SPEC]

# [INFO]
# (no callees)
# [INFO]

def _extracted_func_dir(extracted_base, src_rel):
    """
    Map a source file (relative path, phases.json convention) to the directory holding its
    extracted-function files.

    Mirrors the `zzz.ext -> zzz-ext` derivation used by run_extraction and
    _collect_phase_files: source file <src_dir>/<base>.<ext> is extracted to
    <extracted_base>/<src_dir>/<base>-<ext>/, with one file per function named
    <func_name>.<ext>.
    """
    src_dir = os.path.dirname(src_rel)
    src_base = os.path.basename(src_rel)
    last_dot = src_base.rfind(".")
    if last_dot > 0:
        dir_name = src_base[:last_dot] + "-" + src_base[last_dot + 1:]
    else:
        dir_name = src_base
    if src_dir:
        return os.path.join(extracted_base, src_dir, dir_name)
    return os.path.join(extracted_base, dir_name)

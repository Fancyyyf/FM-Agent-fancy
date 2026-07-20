# [SPEC]
# Unit: src/generate_topdown_layers-py/_collect_phase_files.py
#
# _collect_phase_files(proj_dir, phase_data) -> list[tuple[str, str]]
#
# Pre-condition:
#   - proj_dir is a path to an existing directory
#   - phase_data is a dict that may contain a "modules" key; if present, its value is an iterable of module dicts, each with a "name" (str) and optionally "source_files" (iterable of str relative paths)
#
# Post-condition:
#   - Returns a list of (file_path, module_name) pairs, where module_name is the "name" of a module in phase_data
#   - For each source file declared in a module: the source file's basename extension is stripped by replacing the last "." with "-" (e.g., "loader.cpp" → "loader-cpp"), and the resulting directory name is resolved under proj_dir/extracted_functions/ alongside the source file's parent directory
#   - Every regular file found in such a directory is collected into the result, each paired with the name of the module that declared the source file
#   - Directories that do not exist on disk are skipped with no error raised
#   - Returns an empty list when phase_data has no "modules" key, the modules list is empty, or no extracted-function directories exist on disk
#   - The returned list preserves no guaranteed ordering across calls
# [SPEC]

# [INFO]
# (no callees)
# [INFO]

def _collect_phase_files(proj_dir, phase_data):
    """For a phase, collect all extracted function file paths.

    Returns list of (file_path, module_name) tuples.
    """
    extracted_base = os.path.join(proj_dir, "extracted_functions")
    results = []

    for module in phase_data.get("modules", []):
        module_name = module["name"]
        for src_file in module.get("source_files", []):
            # Derive extracted directory: xxx/yyy/zzz.ext -> xxx/yyy/zzz-ext
            src_dir = os.path.dirname(src_file)
            src_base = os.path.basename(src_file)
            last_dot = src_base.rfind(".")
            if last_dot > 0:
                dir_name = src_base[:last_dot] + "-" + src_base[last_dot + 1:]
            else:
                dir_name = src_base

            func_dir = os.path.join(extracted_base, src_dir, dir_name) if src_dir else os.path.join(extracted_base, dir_name)
            if not os.path.isdir(func_dir):
                continue

            for fname in os.listdir(func_dir):
                fpath = os.path.join(func_dir, fname)
                if os.path.isfile(fpath):
                    results.append((fpath, module_name))

    return results

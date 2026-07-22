# [SPEC]
# Unit: fm_agent/extracted_functions/src/entry_reasoning_pipeline-py/_extracted_file_to_source_rel.py
#
# _extracted_file_to_source_rel(extracted_rel) -> str
#
# Pre-condition:
#   - extracted_rel is a relative path string whose last path component is a
#     function file name, and the path contains at least one directory component
#     that was derived from a source filename by replacing the last dot with a
#     hyphen followed by a known language extension (the "extraction directory
#     component"). The extraction layout is such that the extraction directory
#     component's suffix after its last hyphen matches a key in EXT_TO_LANG.
#
# Post-condition:
#   - Returns the source-file relative path obtained by scanning the path
#     components from right to left (skipping the filename) to find the
#     extraction directory component. Once found, the component's last hyphen
#     and its following extension are replaced by a dot and the extension
#     (e.g., "loader-cpp" -> "loader.cpp"). The resulting filename is
#     prepended with any leading directory prefix (components before the
#     extraction directory component), and the function file component is
#     dropped. If no extraction directory component is found (i.e., no
#     component whose hyphen-suffix is in EXT_TO_LANG), falls back to using
#     the immediate parent directory: its last hyphen is replaced with a dot
#     (if a hyphen exists after the first character), and the result is
#     prefixed with the parent directory of that parent, or used as is if no
#     grandparent exists.
#   - The returned path uses the OS-native path separator (os.sep).
# [SPEC]

# [INFO]
# (no callees)
# [INFO]

def _extracted_file_to_source_rel(extracted_rel):
    """Map an extracted-function file path back to its source file (relative).

    Inverse of the extraction layout: ``src/engine/loader-cpp/loadData.cpp``
    (a function file) -> ``src/engine/loader.cpp`` (the source file). Extraction
    builds the function directory by replacing the source filename's last dot
    with a hyphen (``loader.cpp`` -> ``loader-cpp``). Member functions keep the
    class qualifier in the flat filename (``.../loader-cpp/MyClass::method.cpp``),
    so the ``<base>-<ext>`` directory is the function file's immediate parent; we
    still locate it by scanning the path components from the right (matching a
    component that ends in ``-<known extension>``) so the mapping is robust.
    """
    parts = extracted_rel.split(os.sep)
    for i in range(len(parts) - 2, -1, -1):          # skip the trailing func file
        comp = parts[i]
        hyphen = comp.rfind("-")
        if hyphen > 0 and comp[hyphen + 1:] in EXT_TO_LANG:
            src_dir = os.sep.join(parts[:i])
            source_base = comp[:hyphen] + "." + comp[hyphen + 1:]
            return os.path.join(src_dir, source_base) if src_dir else source_base
    # Fallback: original immediate-parent behaviour (no recognised -ext dir).
    func_dir = os.path.dirname(extracted_rel)
    src_dir = os.path.dirname(func_dir)
    dir_name = os.path.basename(func_dir)
    hyphen = dir_name.rfind("-")
    source_base = dir_name[:hyphen] + "." + dir_name[hyphen + 1:] if hyphen > 0 else dir_name
    return os.path.join(src_dir, source_base) if src_dir else source_base

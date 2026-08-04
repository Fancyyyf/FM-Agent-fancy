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

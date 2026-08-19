def _file_to_fqn(filepath, proj_dir):
    """Convert an extracted function file path to its FQN.

    extracted_functions/src/engine/loader-cpp/loadData.cpp -> src::engine::loader-cpp::loadData
    """
    extracted_base = os.path.join(proj_dir, "extracted_functions")
    rel = os.path.relpath(filepath, extracted_base)
    # Strip file extension from the function file itself
    stem, _ = os.path.splitext(rel)
    # Join with :: separator
    parts = Path(stem).parts
    return "::".join(parts)

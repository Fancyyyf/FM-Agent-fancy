def _src_rel_to_func_dir(proj_dir, abs_src):
    """(func_dir, ext) for a source file: the extracted-functions directory that
    holds its functions (``.../loader-cpp``) and the source extension."""
    extracted_base = os.path.join(proj_dir, "fm_agent", "extracted_functions")
    rel = os.path.relpath(abs_src, proj_dir)
    src_dir = os.path.dirname(rel)
    src_base = os.path.basename(rel)
    last_dot = src_base.rfind(".")
    if last_dot > 0:
        dir_name = src_base[:last_dot] + "-" + src_base[last_dot + 1:]
        ext = src_base[last_dot + 1:]
    else:
        dir_name = src_base
        ext = ""
    func_dir = os.path.join(extracted_base, src_dir, dir_name) if src_dir else os.path.join(extracted_base, dir_name)
    return func_dir, ext

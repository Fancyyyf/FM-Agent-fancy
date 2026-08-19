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

            # Every extracted function is a flat file directly in func_dir, member
            # functions keeping the class qualifier in the name
            # ("<file>-cpp/LocalStorage::Flush.cpp"). os.walk stays robust to any
            # legacy nested file.
            for root, _dirs, fnames in os.walk(func_dir):
                for fname in fnames:
                    fpath = os.path.join(root, fname)
                    if os.path.isfile(fpath) and not _is_metadata_sidecar(fname):
                        results.append((fpath, module_name))

    return results

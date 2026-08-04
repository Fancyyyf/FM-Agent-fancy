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
                        if os.path.isfile(fpath) and not _is_metadata_sidecar(fname):
                            phase_files.append(os.path.relpath(fpath, input_dir))
    return phase_files

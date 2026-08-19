def _write_file_names(file_names, output_path):
    """Write sorted, de-duplicated file names to output_path."""
    file_names = sorted(dict.fromkeys(file_names))
    tmp_path = output_path + ".tmp"
    with open(tmp_path, "w") as f:
        json.dump(file_names, f, indent=2, ensure_ascii=False)
    os.replace(tmp_path, output_path)
    return file_names

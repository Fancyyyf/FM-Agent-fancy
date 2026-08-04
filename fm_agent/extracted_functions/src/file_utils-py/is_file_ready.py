def is_file_ready(file_path):
    """Return whether both metadata sidecars contain valid new-format JSON."""
    spec_path = f"{file_path}.spec.json"
    info_path = f"{file_path}.info.json"

    if not os.path.isfile(spec_path) or not os.path.isfile(info_path):
        return False

    try:
        with open(spec_path, "r", encoding="utf-8") as file:
            spec = json.load(file)
        with open(info_path, "r", encoding="utf-8") as file:
            info = json.load(file)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return False

    return _is_valid_spec_json(spec) and _is_valid_info_json(info)

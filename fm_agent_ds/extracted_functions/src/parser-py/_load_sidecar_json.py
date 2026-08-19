def _load_sidecar_json(file_path, suffix):
    """Read one JSON sidecar next to file_path, or return None when unavailable."""
    try:
        with open(f"{file_path}{suffix}", "r", encoding="utf-8") as file:
            return json.load(file)
    except (OSError, json.JSONDecodeError):
        return None

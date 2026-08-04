def extract_info_block(filepath: Path) -> Optional[dict]:
    """Read the adjacent .info.json object when it is usable."""
    info_path = _info_json_path(filepath)

    try:
        with info_path.open("r", encoding="utf-8") as file:
            info = json.load(file)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None

    return info if isinstance(info, dict) else None

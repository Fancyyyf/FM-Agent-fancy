def _info_json_path(filepath: Path) -> Path:
    """Return the info sidecar next to one extracted function file."""
    return Path(str(filepath) + ".info.json")

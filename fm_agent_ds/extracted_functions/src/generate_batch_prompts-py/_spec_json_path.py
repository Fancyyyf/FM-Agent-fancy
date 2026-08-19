def _spec_json_path(filepath: Path) -> Path:
    """Return the spec sidecar next to one extracted function file."""
    return Path(str(filepath) + ".spec.json")

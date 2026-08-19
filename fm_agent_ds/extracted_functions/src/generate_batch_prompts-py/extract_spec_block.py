def extract_spec_block(filepath: Path) -> Optional[str]:
    """Read .spec.json and rebuild reasoner-facing spec text."""
    spec_path = _spec_json_path(filepath)

    try:
        with spec_path.open("r", encoding="utf-8") as file:
            spec = json.load(file)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None

    if not isinstance(spec, dict):
        return None

    return (
        f"{spec.get('signature', '')}\n\n"
        f"Pre-condition:\n{spec.get('pre_condition', '')}\n\n"
        f"Post-condition:\n{spec.get('post_condition', '')}"
    )

def parse_existing_opencode_config(text: str) -> dict:
    if not text.strip():
        return {}
    try:
        loaded = json.loads(_strip_jsonc(text))
    except json.JSONDecodeError as exc:
        raise ConfigWizardError(
            "Existing OpenCode config is invalid JSON/JSONC; refusing to overwrite it."
        ) from exc
    if not isinstance(loaded, dict):
        raise ConfigWizardError(
            "Existing OpenCode config must be a JSON object at the top level."
        )
    return loaded

def local_backend_toml_updates(env_path: Path, backend: str) -> dict[str, str]:
    """Keep local CLI model choices when migrating dotenv settings into TOML."""
    validate_llm_setting("backend", backend)
    dotenv_settings = dotenv_values(env_path)
    updates = {"backend": backend}
    for env_key, toml_key in (("LLM_MODEL", "name"), ("LLM_EFFORT", "effort")):
        value = dotenv_settings.get(env_key)
        if value is not None:
            updates[toml_key] = value
    for key, value in updates.items():
        validate_llm_setting(key, value)
    return updates

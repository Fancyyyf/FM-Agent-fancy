def apply_llm_settings_update(
    updates: dict[str, str],
    toml_path: Path,
) -> Path | None:
    toml_text = _read_text_if_exists(toml_path)
    if not toml_text:
        raise ConfigWizardError(
            f"fm-agent.toml not found at {toml_path}; refusing to guess a new project config."
        )
    updated_toml = update_llm_settings_toml_text(toml_text, updates)
    try:
        tomllib.loads(updated_toml)
    except tomllib.TOMLDecodeError as exc:  # Defensive: the text editor should preserve TOML.
        raise ConfigWizardError("Generated fm-agent.toml is invalid TOML.") from exc

    backup = backup_file(toml_path)
    atomic_write(toml_path, updated_toml)
    return backup

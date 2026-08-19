def apply_local_backend_configuration(
    backend: str,
    paths: WizardPaths,
) -> tuple[list[tuple[Path, Path | None]], tuple[str, ...]]:
    toml_text = _read_text_if_exists(paths.toml_path)
    if not toml_text:
        raise ConfigWizardError(
            f"fm-agent.toml not found at {paths.toml_path}; refusing to guess a new project config."
        )
    toml_updates = local_backend_toml_updates(paths.env_path, backend)
    updated_toml = update_llm_settings_toml_text(toml_text, toml_updates)
    try:
        tomllib.loads(updated_toml)
    except tomllib.TOMLDecodeError as exc:  # Defensive: the text editor should preserve TOML.
        raise ConfigWizardError("Generated fm-agent.toml is invalid TOML.") from exc

    updated_env, removed_overrides = remove_legacy_llm_env_overrides(
        _read_text_if_exists(paths.env_path)
    )
    backups = [(paths.toml_path, backup_file(paths.toml_path))]
    if removed_overrides:
        backups.append((paths.env_path, backup_file(paths.env_path, private=True)))

    atomic_write(paths.toml_path, updated_toml)
    if removed_overrides:
        atomic_write(paths.env_path, updated_env)
    return backups, removed_overrides

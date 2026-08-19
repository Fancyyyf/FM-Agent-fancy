def apply_configuration(
    config: LLMConfigInput,
    paths: WizardPaths,
    *,
    validate: bool = True,
) -> list[tuple[Path, Path | None]]:
    validate_input(config)

    env_text = _read_text_if_exists(paths.env_path)
    toml_text = _read_text_if_exists(paths.toml_path)
    if not toml_text:
        raise ConfigWizardError(
            f"fm-agent.toml not found at {paths.toml_path}; refusing to guess a new project config."
        )
    opencode_text = _read_text_if_exists(paths.opencode_config_path)
    opencode_secret_path = secret_path_for_provider(config)

    updated_env = update_env_text(env_text, config.api_key)
    updated_toml = update_fm_agent_toml_text(toml_text, config)
    merged_opencode = merge_opencode_config(
        parse_existing_opencode_config(opencode_text),
        config,
        opencode_secret_path=opencode_secret_path,
    )
    if validate:
        validate_generated_state(
            config,
            merged_opencode,
            updated_toml,
            opencode_secret_path=opencode_secret_path,
        )

    backups = [
        (paths.toml_path, backup_file(paths.toml_path)),
        (paths.env_path, backup_file(paths.env_path, private=True)),
        (
            paths.opencode_config_path,
            backup_file(paths.opencode_config_path, private=True),
        ),
        (opencode_secret_path, backup_file(opencode_secret_path, private=True)),
    ]
    atomic_write(paths.toml_path, updated_toml)
    atomic_write(paths.env_path, updated_env)
    opencode_secret_path.parent.mkdir(parents=True, exist_ok=True)
    opencode_secret_path.parent.chmod(0o700)
    atomic_write(opencode_secret_path, config.api_key + "\n")
    opencode_secret_path.chmod(0o600)
    atomic_write(
        paths.opencode_config_path,
        json.dumps(merged_opencode, indent=2, ensure_ascii=False) + "\n",
    )
    return backups

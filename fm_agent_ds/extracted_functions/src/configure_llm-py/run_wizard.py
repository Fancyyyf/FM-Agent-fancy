def run_wizard(project_root: Path) -> int:
    print("FM-Agent LLM configuration")
    backend = _prompt_backend()
    if backend != "opencode":
        print()
        print(
            "Local CLI backends use their own authentication; no API key or OpenCode "
            "provider configuration is required."
        )
        return run_local_backend_configuration(project_root, backend)

    paths = default_paths(project_root)
    print()
    config, validate = prompt_for_config()
    print()
    print(_preview(config, paths))
    print()
    warn_live_llm_environment_overrides()
    if live_llm_environment_overrides():
        print()
    if not _prompt_yes_no("Continue?", default=True):
        print("Aborted.")
        return 1

    backups = apply_configuration(config, paths, validate=validate)
    print(f"✓ Updated {paths.toml_path}")
    print(f"✓ Updated {paths.env_path}")
    print(f"✓ Updated {paths.opencode_config_path}")
    for path, backup in backups:
        if backup is not None:
            print(f"✓ Backed up {path} -> {backup}")
    if validate:
        print("✓ Configuration syntax is valid")
    return 0

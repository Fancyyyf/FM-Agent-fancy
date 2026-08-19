def run_local_backend_configuration(project_root: Path, backend: str) -> int:
    paths = default_paths(project_root)
    _updated_env, removed_overrides = remove_legacy_llm_env_overrides(
        _read_text_if_exists(paths.env_path)
    )
    toml_updates = local_backend_toml_updates(paths.env_path, backend)
    print(
        _preview_local_backend_configuration(
            backend,
            paths,
            removed_overrides,
            toml_updates,
        )
    )
    print()
    warn_live_llm_environment_overrides()
    if live_llm_environment_overrides():
        print()
    if not _prompt_yes_no("Continue?", default=True):
        print("Aborted.")
        return 1

    backups, removed_overrides = apply_local_backend_configuration(backend, paths)
    print(f"Updated {paths.toml_path}")
    if removed_overrides:
        print(f"Removed legacy LLM overrides from {paths.env_path}")
    for path, backup in backups:
        if backup is not None:
            print(f"Backed up {path} -> {backup}")
    return 0

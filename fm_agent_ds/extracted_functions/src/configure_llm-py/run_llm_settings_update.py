def run_llm_settings_update(
    project_root: Path,
    updates: dict[str, str],
    *,
    assume_yes: bool = False,
) -> int:
    paths = default_paths(project_root)
    toml_path = paths.toml_path
    print(_preview_llm_settings_update(updates, toml_path))
    print()
    has_dotenv_override = warn_dotenv_overrides_for_updates(paths.env_path, updates)
    warn_live_llm_environment_overrides()
    if has_dotenv_override or live_llm_environment_overrides():
        print()
    if not assume_yes and not _prompt_yes_no("Continue?", default=True):
        print("Aborted.")
        return 1

    backup = apply_llm_settings_update(updates, toml_path)
    print(f"Updated {toml_path}")
    if backup is not None:
        print(f"Backed up {toml_path} -> {backup}")
    return 0

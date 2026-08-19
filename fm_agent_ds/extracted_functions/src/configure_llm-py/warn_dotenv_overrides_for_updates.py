def warn_dotenv_overrides_for_updates(
    env_path: Path,
    updates: dict[str, str],
) -> bool:
    """Warn when the focused TOML update remains shadowed by project dotenv."""
    _updated_env, legacy_overrides = remove_legacy_llm_env_overrides(
        _read_text_if_exists(env_path)
    )
    shadowing = tuple(
        name
        for name in legacy_overrides
        if _TOML_KEY_BY_ENV_KEY[name] in updates
    )
    if not shadowing:
        return False
    print("Warning: these project .env variables still override this TOML update:")
    print(f"  {', '.join(shadowing)}")
    print("The set command does not modify .env. Remove those lines, or run the")
    print("interactive wizard to migrate legacy LLM overrides.")
    return True

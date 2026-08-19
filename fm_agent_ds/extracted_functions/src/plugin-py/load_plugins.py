def load_plugins(plugins_dir: Path) -> Dict[str, PluginConfig]:
    """Scan *plugins_dir* for subdirectories, validate each, return valid plugins.

    Invalid plugins are printed with their error reason and skipped.
    """
    if not plugins_dir.is_dir():
        return {}

    plugins = {}
    for entry in sorted(plugins_dir.iterdir()):
        if not entry.is_dir():
            continue
        if entry.name.startswith(".") or entry.name == "__pycache__":
            continue
        config = validate_plugin(entry)
        if config is not None:
            plugins[config.name] = config
    return plugins

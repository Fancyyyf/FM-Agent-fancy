def validate_plugin(plugin_dir: Path) -> Optional[PluginConfig]:
    """Validate a single plugin directory.

    Returns a ``PluginConfig`` if the plugin is valid, otherwise ``None``
    (after printing validation errors to stdout).
    """
    name = plugin_dir.name
    plugin_json = plugin_dir / "plugin.json"
    plugin_config_json = plugin_dir / "plugin.config.json"

    if not plugin_json.is_file():
        if plugin_config_json.is_file():
            print(
                f"Invalid plugin '{name}': found plugin.config.json "
                "but expected plugin.json"
            )
        else:
            print(f"Invalid plugin '{name}': plugin.json not found")
        return None

    try:
        with open(plugin_json, "r") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError) as exc:
        print(
            f"Invalid plugin '{name}': failed to parse plugin.json — {exc}"
        )
        return None

    if not isinstance(data, dict):
        print(
            f"Invalid plugin '{name}': plugin.json must be a JSON object"
        )
        return None

    return _validate_plugin_json_content(plugin_dir, name, data)

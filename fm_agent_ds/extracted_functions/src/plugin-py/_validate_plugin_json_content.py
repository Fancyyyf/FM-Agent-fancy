def _validate_plugin_json_content(
    plugin_dir: Path, name: str, data: dict
) -> Optional[PluginConfig]:
    """Validate the content of a parsed plugin.json; returns PluginConfig or None."""
    plugin_name = data.get("name", "")
    if plugin_name != name:
        print(
            f"Invalid plugin '{name}': plugin name mismatch "
            f"(expected '{name}', got '{plugin_name}')"
        )
        return None

    if not data.get("version"):
        print(f"Invalid plugin '{name}': 'version' field is missing or empty")
        return None

    stages = {}
    stages_data = data.get("stages", {})
    if not isinstance(stages_data, dict):
        print(f"Invalid plugin '{name}': 'stages' must be a JSON object")
        return None

    for stage_name, stage_data in stages_data.items():
        if not isinstance(stage_data, dict):
            print(
                f"Invalid plugin '{name}': stage '{stage_name}' "
                "must be a JSON object"
            )
            return None
        stage = PluginStageConfig.from_dict(stage_data)
        errors = stage.validated()
        if errors:
            for err in errors:
                print(
                    f"Invalid plugin '{name}': stage '{stage_name}' — {err}"
                )
            return None
        if stage.type == "modify" and stage.input_md:
            input_path = plugin_dir / stage.input_md
            if not input_path.is_file():
                print(
                    f"Invalid plugin '{name}': stage '{stage_name}' — "
                    f"input_md '{stage.input_md}' not found in plugin directory"
                )
                return None
        stages[stage_name] = stage

    return PluginConfig(
        name=plugin_name,
        version=data["version"],
        root=plugin_dir,
        stages=stages,
    )

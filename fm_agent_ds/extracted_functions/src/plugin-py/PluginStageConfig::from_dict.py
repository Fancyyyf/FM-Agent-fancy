    def from_dict(data: dict) -> "PluginStageConfig":
        return PluginStageConfig(
            type=data.get("type", ""),
            replace_cmd=data.get("replace_cmd"),
            input_md=data.get("input_md"),
            output_process=data.get("output_process"),
        )

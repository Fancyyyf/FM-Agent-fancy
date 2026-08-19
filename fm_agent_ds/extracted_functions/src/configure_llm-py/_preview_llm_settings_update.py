def _preview_llm_settings_update(updates: dict[str, str], toml_path: Path) -> str:
    labels = {
        "name": "Model ID",
        "provider": "Provider ID",
        "base_url": "Base URL",
        "backend": "Backend",
        "effort": "Reasoning effort",
        "api_style": "API protocol",
    }
    settings = [f"{labels[key]}: {value!r}" for key, value in updates.items()]
    return "\n".join(
        [
            "FM-Agent LLM settings update",
            "",
            *settings,
            "",
            "Only the following file will be updated:",
            f"  - {toml_path}",
            "",
            "This command does not change .env or the standalone OpenCode config.",
        ]
    )

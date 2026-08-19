def build_provider_entry(config: LLMConfigInput, opencode_secret_path: Path) -> dict:
    return {
        "npm": adapter_for_api_style(config.api_style),
        "options": {
            "baseURL": config.base_url,
            "apiKey": f"{{file:{opencode_secret_path}}}",
        },
        "models": {
            config.model_id: {},
        },
    }

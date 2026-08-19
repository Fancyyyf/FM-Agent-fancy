def update_fm_agent_toml_text(text: str, config: LLMConfigInput) -> str:
    return update_llm_settings_toml_text(
        text,
        {
            "name": config.model_id,
            "provider": config.provider_id,
            "base_url": config.base_url,
            "backend": config.backend,
            "api_style": config.api_style,
        },
    )

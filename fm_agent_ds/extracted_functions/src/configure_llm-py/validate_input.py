def validate_input(config: LLMConfigInput) -> None:
    if not config.provider_id.strip():
        raise ConfigWizardError("Provider ID must not be empty.")
    if not config.provider_name.strip():
        raise ConfigWizardError("Provider name must not be empty.")
    if not config.model_id.strip():
        raise ConfigWizardError("Model ID must not be empty.")
    if not config.api_key.strip():
        raise ConfigWizardError("API key must not be empty.")
    validate_base_url(config.base_url.strip())
    adapter_for_api_style(config.api_style)
    validate_llm_setting("backend", config.backend)

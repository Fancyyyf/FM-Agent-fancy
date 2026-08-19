def prompt_for_config() -> tuple[LLMConfigInput, bool]:
    provider_id = _prompt("Provider ID", "openrouter")
    provider_name = _prompt("Provider name", provider_id.title())
    print()
    print("API protocol:")
    print("  1. OpenAI-compatible")
    print("  2. Anthropic-compatible")
    selected = _prompt("Select", "1")
    api_style: ApiStyle
    if selected == "2":
        api_style = "anthropic"
    elif selected == "1":
        api_style = "openai"
    else:
        raise ConfigWizardError("Protocol selection must be 1 or 2.")

    default_base = (
        "https://openrouter.ai/api/v1"
        if api_style == "openai"
        else "https://api.anthropic.com/v1"
    )
    base_url = _prompt("API base URL", default_base)
    model_id = _prompt("Model ID")
    api_key = getpass("API key: ").strip()
    validate = _prompt_yes_no("Validate generated configuration?", default=True)
    config = LLMConfigInput(
        provider_id=provider_id,
        provider_name=provider_name,
        api_style=api_style,
        base_url=base_url,
        model_id=model_id,
        api_key=api_key,
    )
    return config, validate

def adapter_for_api_style(api_style: ApiStyle) -> str:
    if api_style == "anthropic":
        return "@ai-sdk/anthropic"
    if api_style == "openai":
        return "@ai-sdk/openai-compatible"
    raise ConfigWizardError(f"Unsupported API style: {api_style}")

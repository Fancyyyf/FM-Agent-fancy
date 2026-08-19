def validate_generated_state(
    config: LLMConfigInput,
    merged_opencode: dict,
    updated_toml: str,
    *,
    opencode_secret_path: Path,
) -> None:
    validate_input(config)
    json.dumps(merged_opencode)
    tomllib.loads(updated_toml)

    providers = merged_opencode.get("provider")
    if not isinstance(providers, dict) or config.provider_id not in providers:
        raise ConfigWizardError(
            f"Generated OpenCode config is missing provider '{config.provider_id}'."
        )
    entry = providers[config.provider_id]
    if not isinstance(entry, dict):
        raise ConfigWizardError(
            f"Generated OpenCode provider '{config.provider_id}' is not an object."
        )
    if entry.get("npm") != adapter_for_api_style(config.api_style):
        raise ConfigWizardError(
            "Generated OpenCode adapter does not match the selected API protocol."
        )
    options = entry.get("options")
    if (
        not isinstance(options, dict)
        or options.get("apiKey") != f"{{file:{opencode_secret_path}}}"
    ):
        raise ConfigWizardError(
            "Generated OpenCode config does not reference the saved key file."
        )
    models = entry.get("models")
    if not isinstance(models, dict) or config.model_id not in models:
        raise ConfigWizardError(
            f"Generated OpenCode config is missing model '{config.model_id}'."
        )

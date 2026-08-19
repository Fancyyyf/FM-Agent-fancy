def merge_opencode_config(
    existing: dict,
    config: LLMConfigInput,
    *,
    opencode_secret_path: Path,
) -> dict:
    merged = deepcopy(existing)
    if "$schema" not in merged:
        merged["$schema"] = SCHEMA_URL

    providers = merged.get("provider")
    if providers is None:
        providers = {}
    if not isinstance(providers, dict):
        raise ConfigWizardError("OpenCode config field 'provider' must be an object.")

    entry = providers.get(config.provider_id)
    if entry is None:
        entry = {}
    if not isinstance(entry, dict):
        raise ConfigWizardError(
            f"OpenCode provider '{config.provider_id}' must be a JSON object."
        )

    merged_entry = deepcopy(entry)
    merged_entry["npm"] = adapter_for_api_style(config.api_style)

    options = merged_entry.get("options")
    if options is None:
        options = {}
    if not isinstance(options, dict):
        raise ConfigWizardError(
            f"OpenCode provider '{config.provider_id}.options' must be an object."
        )
    options = dict(options)
    options["baseURL"] = config.base_url
    options["apiKey"] = f"{{file:{opencode_secret_path}}}"
    merged_entry["options"] = options

    models = merged_entry.get("models")
    if models is None:
        models = {}
    if not isinstance(models, dict):
        raise ConfigWizardError(
            f"OpenCode provider '{config.provider_id}.models' must be an object."
        )
    models = dict(models)
    existing_model = models.get(config.model_id)
    if existing_model is None:
        existing_model = {}
    if not isinstance(existing_model, dict):
        raise ConfigWizardError(
            f"OpenCode model entry '{config.provider_id}/{config.model_id}' must be an object."
        )
    models[config.model_id] = existing_model
    merged_entry["models"] = models

    providers = dict(providers)
    providers[config.provider_id] = merged_entry
    merged["provider"] = providers
    return merged

def validate_llm_setting(key: str, value: str) -> None:
    """Validate one non-secret [llm] setting accepted by the lightweight CLI."""
    if key not in _LLM_TOML_KEYS:
        raise ConfigWizardError(f"Unsupported LLM setting: {key}")
    if key == "provider" and not value.strip():
        raise ConfigWizardError("Provider ID must not be empty.")
    if key == "base_url":
        validate_base_url(value.strip())
    elif key == "backend" and value not in _BACKENDS:
        supported = ", ".join(_BACKENDS)
        raise ConfigWizardError(
            f"Backend must be one of: {supported}; got: {value!r}"
        )
    elif key == "api_style":
        adapter_for_api_style(value)  # type: ignore[arg-type]

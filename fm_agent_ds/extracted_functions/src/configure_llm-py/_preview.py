def _preview(config: LLMConfigInput, paths: WizardPaths) -> str:
    secret_path = secret_path_for_provider(config)
    return "\n".join(
        [
            "FM-Agent LLM configuration",
            "",
            f"Provider ID:   {config.provider_id}",
            f"Provider name: {config.provider_name}",
            f"API protocol:  {config.api_style}",
            f"Base URL:      {config.base_url}",
            f"Model ID:      {config.model_id}",
            f"API key:       {mask_secret(config.api_key)}",
            "",
            "The following files will be updated:",
            f"  - {paths.toml_path}",
            f"  - {paths.env_path}",
            f"  - {paths.opencode_config_path}",
            f"  - {secret_path}",
        ]
    )

def secret_path_for_provider(config: LLMConfigInput) -> Path:
    safe_provider_id = re.sub(r"[^A-Za-z0-9._-]+", "_", config.provider_id).strip("._-")
    if not safe_provider_id:
        safe_provider_id = "provider"
    digest = hashlib.sha256(config.provider_id.encode("utf-8")).hexdigest()[:10]
    return _private_opencode_secret_dir() / (
        f"fm-agent-opencode-api-key.{safe_provider_id}.{digest}"
    )

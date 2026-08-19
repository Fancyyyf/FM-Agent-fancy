def _fm_agent_config_path(project_root: Path) -> Path:
    """Match config.py's FM_AGENT_CONFIG path selection exactly."""
    explicit_config = os.environ.get("FM_AGENT_CONFIG")
    if explicit_config is None:
        # config.py loads the project .env without replacing a real process value.
        explicit_config = dotenv_values(project_root / ".env").get("FM_AGENT_CONFIG")
    return Path(explicit_config) if explicit_config else project_root / "fm-agent.toml"

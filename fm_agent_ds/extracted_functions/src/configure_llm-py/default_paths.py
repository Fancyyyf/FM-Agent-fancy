def default_paths(project_root: Path) -> WizardPaths:
    return WizardPaths(
        project_root=project_root,
        env_path=project_root / ".env",
        toml_path=_fm_agent_config_path(project_root),
        opencode_config_path=detect_opencode_config_path(),
    )

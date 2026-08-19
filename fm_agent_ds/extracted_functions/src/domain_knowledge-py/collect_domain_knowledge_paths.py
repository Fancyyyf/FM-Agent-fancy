def collect_domain_knowledge_paths(cli_paths, base_dir, fallback_base_dir=None):
    """Collect markdown paths from CLI values plus FM_AGENT_DOMAIN_KNOWLEDGE."""
    paths = []
    paths.extend(_split_env_paths(settings.runtime.domain_knowledge_paths))
    paths.extend(_flatten_paths(cli_paths))
    return resolve_domain_knowledge_paths(
        paths,
        base_dir=base_dir,
        fallback_base_dir=fallback_base_dir,
    )

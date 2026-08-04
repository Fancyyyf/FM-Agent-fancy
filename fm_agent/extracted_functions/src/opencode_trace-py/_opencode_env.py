def _opencode_env(work_dir, event_id):
    env = os.environ.copy()
    trace_dir = os.path.abspath(os.path.join(_trace_dir(work_dir), "opencode"))
    os.makedirs(trace_dir, exist_ok=True)
    env["TRACE_DIR"] = trace_dir
    env["TRACE_FILENAME"] = event_id
    provider_config = _opencode_provider_config()
    if provider_config is not None:
        # Make the resolved key available under LLM_API_KEY so the injected
        # `{env:LLM_API_KEY}` resolves regardless of where config read it from.
        env["LLM_API_KEY"] = settings.llm.api_key
        # Merge our provider block into any OPENCODE_CONFIG_CONTENT the caller
        # already set (rather than overwriting it), so their inline plugins /
        # permissions / MCP / agents survive; our provider still wins on the
        # provider key it defines.
        existing = {}
        raw = env.get("OPENCODE_CONFIG_CONTENT")
        if raw:
            try:
                loaded = json.loads(raw)
            except (json.JSONDecodeError, TypeError):
                loaded = None
            if isinstance(loaded, dict):
                existing = loaded
        env["OPENCODE_CONFIG_CONTENT"] = json.dumps(_deep_merge(existing, provider_config))
    # subprocess.Popen(cwd=...) chdirs the child but doesn't sync PWD; opencode
    # walks PWD upward looking for AGENTS.md, so without this it picks up the
    # fm-agent repo's own AGENTS.md instead of the target's, baking ~10K bytes
    # of repo docs into every system prompt and invalidating the cache prefix
    # on every edit.
    proj_dir = os.path.dirname(os.path.abspath(work_dir))
    env["PWD"] = proj_dir
    return env

# [SPEC]
# Unit: src/opencode_trace.py
#
# _opencode_env(work_dir, event_id) -> dict
#
# Pre-condition:
#   - work_dir is a path to an existing directory on the filesystem (the fm_agent/
#     workspace directory)
#   - event_id is a non-empty string uniquely identifying a trace event
#
# Post-condition:
#   - Returns a copy of the current process environment (os.environ) with several
#     additional entries applied:
#     - TRACE_DIR: absolute path of the "opencode" subdirectory under the trace
#       directory derived from work_dir; the directory at TRACE_DIR is created if it
#       does not already exist.
#     - TRACE_FILENAME: set to the value of event_id.
#     - PWD: absolute path of the parent directory of work_dir (the project root
#       directory).
#     - If `_opencode_provider_config()` returns a non‑None value (expected to be a
#       dict), then:
#         - LLM_API_KEY is set to the value of `settings.llm.api_key` at call time.
#         - OPENCODE_CONFIG_CONTENT is set to the JSON serialization of a dict
#           produced by deep‑merging any pre‑existing OPENCODE_CONFIG_CONTENT from the
#           original environment with the provider config dict returned by
#           `_opencode_provider_config()`.  The merge gives precedence to the provider
#           config for overlapping keys, while preserving other keys from the
#           original environment.  If the original OPENCODE_CONFIG_CONTENT is not a
#           valid JSON object, it is treated as an empty dict for the merge.
#     - If `_opencode_provider_config()` returns None, no LLM_API_KEY or
#       OPENCODE_CONFIG_CONTENT entries are added (the environment copy may still
#       inherit those keys from the original os.environ unchanged).
#   - All other entries present in the calling process's environment at the time of
#     the call are preserved, except where explicitly overwritten by the rules above.
# [SPEC]

# [INFO]
# _trace_dir(work_dir) -> str
#   Pre-condition: work_dir is a filesystem path
#   Post-condition: Returns a path string representing the trace data directory
#     under work_dir
#
# _opencode_provider_config() -> Optional[dict]
#   Pre-condition: The settings module is initialized (settings.llm is available)
#   Post-condition: Returns either a dict containing the opencode provider
#     configuration (including the resolved LLM provider settings) or None if no
#     provider configuration is available.
#
# _deep_merge(base: dict, overlay: dict) -> dict
#   Pre-condition: base and overlay are dictionaries
#   Post-condition: Returns a new dict without modifying base or overlay.
#     Result contains all keys from both dictionaries. For keys only in one
#     dict the corresponding value is taken unchanged. For keys present in
#     both, nested dicts are merged recursively using these same rules;
#     otherwise the value from overlay is used.
# [INFO]

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

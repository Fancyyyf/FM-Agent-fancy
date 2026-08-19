def live_llm_environment_overrides() -> tuple[str, ...]:
    """Return real process overrides; the wizard must not alter its caller's shell."""
    return tuple(name for name in _LLM_ENV_KEYS if name in os.environ)

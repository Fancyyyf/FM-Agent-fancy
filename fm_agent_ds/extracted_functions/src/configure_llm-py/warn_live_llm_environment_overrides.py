def warn_live_llm_environment_overrides() -> None:
    overrides = live_llm_environment_overrides()
    if not overrides:
        return
    print("Warning: these shell environment variables override the saved LLM settings:")
    print(f"  {', '.join(overrides)}")
    print("The wizard cannot change the shell that launched it. Before starting FM-Agent")
    print("in this shell, unset them to use the saved configuration:")
    print(f"  unset {' '.join(overrides)}")

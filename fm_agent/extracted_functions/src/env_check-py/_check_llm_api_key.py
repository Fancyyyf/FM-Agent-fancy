def _check_llm_api_key(config):
    ok = bool(config.LLM_API_KEY and config.LLM_API_KEY not in (
        "", "YOUR_LLM_API_KEY",
        "sk-or-v1-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
    ))
    return ok, "LLM_API_KEY is not set in .env file" if not ok else None

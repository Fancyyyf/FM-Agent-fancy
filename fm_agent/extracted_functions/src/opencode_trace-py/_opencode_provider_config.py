# [SPEC]
# Unit: src/opencode_trace.py
#
# _opencode_provider_config() -> dict | None
#
# Pre-condition:
#   - The global settings object has been loaded and its .llm attribute provides
#     access to the LLM configuration fields api_key, base_url, name, provider,
#     and api_style.
#
# Post-condition:
#   - Returns None when any of api_key, base_url, name, or provider is falsy
#     (i.e., an empty string, None, or otherwise evaluates to False).
#   - When all of api_key, base_url, name, and provider are truthy, returns a
#     dict that, when included in an OpenCode configuration, defines a valid
#     provider.
#   - The returned dict nests under a "provider" key, keyed by the value of the
#     provider setting, and contains an npm adapter package name, a base URL, a
#     model name, and an API key reference.
#   - The npm adapter is chosen based on the api_style setting: the Anthropic SDK
#     package when api_style is "anthropic", and an OpenAI-compatible SDK package
#     otherwise.
#   - The API key is specified as an environment-variable reference
#     ({env:LLM_API_KEY}) rather than a literal key value.
#   - The function has no side effects: it does not mutate any global state,
#     perform I/O, or modify any passed-in arguments.
#   - No exceptions are raised under normal operation.
# [SPEC]

def _opencode_provider_config():
    """Build an OpenCode ``provider`` block from FM-Agent's own LLM settings.

    ``fm-agent.toml`` is the single source of truth for provider / base URL /
    model: instead of the user hand-writing (and keeping in sync) a provider
    block in ``~/.config/opencode/opencode.json``, FM-Agent injects an equivalent
    block into the OpenCode subprocess via ``OPENCODE_CONFIG_CONTENT``. That is
    OpenCode's highest-precedence config source, so it wins over any same-named
    provider in the user's ``opencode.json``; OpenCode deep-merges per key, so
    other providers and the ``plugin`` array in that file are preserved.

    Returns ``None`` (injecting nothing) unless we have every field needed to
    build a working block — provider, base URL, model, and an API key. Without a
    key the injected ``{env:LLM_API_KEY}`` would be empty and would clobber a
    working config, so we stay out of the way and leave OpenCode's own config in
    effect.
    """
    llm = settings.llm
    if not (llm.api_key and llm.base_url and llm.name and llm.provider):
        return None
    adapter = (
        "@ai-sdk/anthropic"
        if llm.api_style == "anthropic"
        else "@ai-sdk/openai-compatible"
    )
    return {
        "provider": {
            llm.provider: {
                "npm": adapter,
                "options": {
                    "baseURL": llm.base_url,
                    # Resolved by OpenCode from the child env (set below), so the
                    # key is never written to a config file on disk.
                    "apiKey": "{env:LLM_API_KEY}",
                },
                "models": {llm.name: {}},
            }
        }
    }

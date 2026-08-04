def _is_anthropic_model(model):
    """True if model should be routed through anthropic-native /v1/messages."""
    m = (model or "").lower()
    return m.startswith("claude") or m.startswith("anthropic/")

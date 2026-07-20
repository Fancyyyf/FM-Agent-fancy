# [SPEC]
# Unit: src/llm_client-py/_is_anthropic_model.py
#
# _is_anthropic_model(model) -> bool
#
# Pre-condition:
#   - model is a model-identifier string, or a falsy value (None, empty string, etc.)
#
# Post-condition:
#   - Returns True when model, after coercion to lowercase, starts with the prefix "claude" or "anthropic/"
#   - Returns False for all other model identifiers, including when model is None, empty, or otherwise falsy
#   - The caller routes the model through the Anthropic-native /v1/messages endpoint when this function returns True, and through the standard chat-completions endpoint otherwise
# [SPEC]

# [INFO]
# (no callees)
# [INFO]

def _is_anthropic_model(model):
    """True if model should be routed through anthropic-native /v1/messages."""
    m = (model or "").lower()
    return m.startswith("claude") or m.startswith("anthropic/")

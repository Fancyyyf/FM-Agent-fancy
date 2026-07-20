# [SPEC]
# Unit: fm_agent/extracted_functions/dashboard-py/_cost_from_usage.py
#
# _cost_from_usage(model, usage) -> float
#
# Pre-condition:
#   - model is a string identifying an LLM model, or None
#   - usage is a dict whose values are non-negative numeric token counts,
#     or None / a falsy value
#
# Post-condition:
#   - Returns a non-negative float representing the total cost in USD of
#     the token consumption recorded in usage, priced according to the
#     per-token rates of the model's known pricing tier
#   - Four token categories are recognized: input tokens, output tokens,
#     cache-read tokens, and cache-creation tokens; each is priced at a
#     distinct per-token rate determined independently by the model's
#     pricing tier
#   - A token category not present in usage, or present with a falsy
#     value, contributes zero to the total
#   - A pricing component not present in the model's tier contributes
#     zero to the total
#   - Returns 0.0 when model is None, usage is falsy, or no pricing tier
#     is associated with model
# [SPEC]

# [INFO]
# _price_for(model) -> dict | None
#   Pre-condition: model is a string identifying an LLM model
#   Post-condition: Returns a dict mapping per-token pricing component
#     names to positive float values representing the cost per token in
#     USD for that component, or a falsy value when pricing data for the
#     model is unavailable
# [INFO]

def _cost_from_usage(model, usage):
    """Return USD cost for one anthropic-style usage dict, or 0 if unknown."""
    p = _price_for(model)
    if not p or not usage:
        return 0.0
    inp = usage.get("input_tokens", 0) or 0
    out = usage.get("output_tokens", 0) or 0
    cr = usage.get("cache_read_input_tokens", 0) or 0
    cw = usage.get("cache_creation_input_tokens", 0) or 0
    return (
        inp * (p.get("input_cost_per_token") or 0)
        + out * (p.get("output_cost_per_token") or 0)
        + cr * (p.get("cache_read_input_token_cost") or 0)
        + cw * (p.get("cache_creation_input_token_cost") or 0)
    )

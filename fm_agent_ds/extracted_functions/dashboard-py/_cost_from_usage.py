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

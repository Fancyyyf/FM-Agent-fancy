def _price_for(model):
    if not model:
        return None
    key = model
    if key in _MODEL_COST:
        return _MODEL_COST[key]
    # try stripping a "provider/" prefix
    if "/" in key:
        bare = key.split("/", 1)[1]
        if bare in _MODEL_COST:
            return _MODEL_COST[bare]
    return None

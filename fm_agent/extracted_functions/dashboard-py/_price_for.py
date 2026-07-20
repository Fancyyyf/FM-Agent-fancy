# [SPEC]
# Unit: fm_agent/extracted_functions/dashboard-py/_price_for.py
#
# _price_for(model) -> Optional[dict]
#
# Pre-condition:
#   - model is a string, or None / a falsy value
#
# Post-condition:
#   - Returns a dict whose keys are per-token pricing component names and
#     whose values are positive float per-token costs in USD for the model
#     identified by model, or None when no pricing data is available
#   - A model identifier that contains a "/" character (provider-prefixed
#     form such as "provider/model") is recognized under both its full
#     provider-prefixed form and its bare form (the substring following the
#     first "/"); a match in either form is sufficient
#   - Returns None when model is falsy, or when the model identifier has no
#     matching pricing data in either its full or bare form
# [SPEC]

# [INFO]
# (no callees)
# [INFO]

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

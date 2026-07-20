# [SPEC]
# Unit: src/llm_client.py
#
# _should_inject_user_id(base_url) -> bool
#
# Pre-condition:
#   - base_url is a string or a falsy value (which is treated as an empty string)
#
# Post-condition:
#   - Returns True when the given base URL, with any trailing forward-slash characters removed, matches at least one entry in the predefined provider-specific set of URL patterns that require user-id metadata injection into request bodies
#   - Returns False when the normalized base URL matches none of those predefined injection-target patterns
# [SPEC]

# [INFO]
# _matches_inject_target(url, target) -> bool
#   Pre-condition: url is a non-empty string with trailing slashes removed; target is a provider-specific URL pattern from the injection-target set
#   Post-condition: Returns True when url is a sub-path of or matches target according to a provider-defined matching rule; returns False otherwise
# [SPLIT]
# _inject_targets() -> iterable of str
#   Pre-condition: None (takes no arguments)
#   Post-condition: Returns the complete, fixed collection of provider-specific URL patterns for which user-id metadata must be injected into request bodies
# [INFO]

def _should_inject_user_id(base_url):
    url = (base_url or "").rstrip("/")
    return any(_matches_inject_target(url, target) for target in _inject_targets())

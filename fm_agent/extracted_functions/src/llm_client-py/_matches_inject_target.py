# [SPEC]
# Unit: src/llm_client.py
#
# _matches_inject_target(url, target) -> bool
#
# Pre-condition:
#   - url is a non-empty string whose trailing slash characters have been removed by the caller
#   - target is a non-empty string from the provider-specific set of URL patterns requiring user-id injection
#
# Post-condition:
#   - When target is an absolute URL prefix, returns True if and only if url begins with target as a string prefix — covering all paths at or beneath the target's path hierarchy
#   - When target is a hostname, returns True if and only if the hostname that url refers to is either exactly equal to target, or is a subdomain of target (the hostname ends with a period followed by target)
#   - Returns False when url does not satisfy either matching rule — including when url refers to a hostname unrelated to target, or when url cannot be resolved to a hostname while target is a hostname
# [SPEC]

# [INFO]
# (no callees)
# [INFO]

def _matches_inject_target(url, target):
    if target.lower().startswith(("http://", "https://")):
        return url.startswith(target)
    try:
        host = urllib.parse.urlparse(url).hostname or ""
    except Exception:
        return False
    return host == target or host.endswith("." + target)

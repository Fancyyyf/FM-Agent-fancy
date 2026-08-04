"""Probe: confirm _inject_targets crashes on truthy non-string settings.inject.hosts."""

import sys
import types

# -- Build a minimal mock for the "settings" global that the function expects --
# The buggy code is: settings.inject.hosts.split(",")
# If hosts is a truthy non-string (e.g. a list), .split(",") raises AttributeError.
# The spec requires: returns a list of non-empty strings; empty list when nothing configured.

settings_mod = types.ModuleType("settings")

class InjectConfig:
    hosts = ["api.openai.com", "api.anthropic.com"]  # LIST — the trigger

settings_mod.inject = InjectConfig()
sys.modules["settings"] = settings_mod
settings = settings_mod  # make 'settings' visible in module globals so functions resolve it

# -- Define the functions exactly as they appear in the extracted source --
def _inject_targets():
    return [s.strip() for s in (settings.inject.hosts or "").split(",") if s.strip()]

def _matches_inject_target(url, target):
    if target.lower().startswith(("http://", "https://")):
        return url.startswith(target)
    try:
        host = __import__("urllib.parse", fromlist=["urlparse"]).urlparse(url).hostname or ""
    except Exception:
        return False
    return host == target or host.endswith("." + target)

def _should_inject_user_id(base_url):
    """Public entry point — exercises _inject_targets indirectly."""
    url = (base_url or "").rstrip("/")
    return any(_matches_inject_target(url, target) for target in _inject_targets())

# -- Execute the test through the public API (_should_inject_user_id) --
try:
    result = _should_inject_user_id("https://api.openai.com/v1/chat/completions")
    # If we reach here, the bug was NOT reproduced
    print(f"NOT CONFIRMED — _should_inject_user_id returned {result!r} without crashing")
except AttributeError as e:
    # Bug confirmed: .split(",") called on a list
    print(f"CONFIRMED — AttributeError on truthy non-string input: {e}")
except Exception as e:
    print(f"ERROR: {type(e).__name__}: {e}")

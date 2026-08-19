"""Probe script for bug: _matches_inject_target case-sensitive hostname comparison.

Bug ID: src--llm_client-py--_matches_inject_target
Spec claim: hostname matching should be case-insensitive.
Actual: host == target comparison is case-sensitive.
"""

import sys
import os

# Isolate runtime: use a temp workspace, not the active fm_agent/ directory.
os.chdir("/tmp/fm_agent_probe_ws")

# Add the FM-Agent repo root to sys.path so 'src' and 'config' are importable.
_REPO_ROOT = "/home/fancy/Projects_Vault/FM-Agent"
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

try:
    from src.llm_client import _matches_inject_target
except Exception as exc:
    print(f"ERROR: cannot import _matches_inject_target: {exc}")
    sys.exit(1)

result = None
passed = False

# --- Test: uppercase target should match lowercase hostname ---
try:
    url = "http://example.com/some/path"
    target = "EXAMPLE.COM"
    actual = _matches_inject_target(url, target)
    # Per DNS spec (RFC 4343), hostnames are case-insensitive.
    # "example.com" and "EXAMPLE.COM" refer to the same host.
    expected = True
    passed = actual != expected  # bug reproduced when actual != expected
except Exception as exc:
    print(f"ERROR: {exc}")
    sys.exit(1)

if passed:
    print(f"CONFIRMED — url={url!r}, target={target!r}, actual={actual!r}, expected={expected!r}")
else:
    print(f"NOT CONFIRMED — actual matched expected: {actual!r}")

#!/usr/bin/env python3
"""Probe script for bug: detect_opencode_config_path - home parameter fallback violation.

Attempt 2: test with a falsy non-None value to verify the `or` fallback.
"""
import os
import sys
import tempfile
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT))

_tmpdir = tempfile.mkdtemp(prefix="probe_detect_opencode_config_path_")
os.chdir(_tmpdir)

for _key in ("OPENCODE_CONFIG", "OPENCODE_CONFIG_DIR", "XDG_CONFIG_HOME", "APPDATA"):
    os.environ.pop(_key, None)

try:
    from src.configure_llm import detect_opencode_config_path

    # home=0: falsy integer (0 is not None, so spec requires using it).
    # Code: `0 or Path.home()` → Path.home() — violates "when home is not None" spec.
    result_with_zero = detect_opencode_config_path(home=0)  # type: ignore
    result_with_none = detect_opencode_config_path(home=None)

    bug_reproduced = result_with_zero == result_with_none

except Exception as exc:
    print(f"ERROR: {exc}")
    sys.exit(1)

if bug_reproduced:
    print(
        f"CONFIRMED — actual (home=0): {result_with_zero!r}"
        f" | expected: would use 0 directly, not fall back to None ({result_with_none!r})"
    )
else:
    print(
        f"NOT CONFIRMED — home=0 result: {result_with_zero!r}"
        f" | none-home result: {result_with_none!r}"
    )

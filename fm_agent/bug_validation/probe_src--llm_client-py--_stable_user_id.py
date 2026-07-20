"""Probe script for bug src--llm_client-py--_stable_user_id.

Spec claim: _stable_user_id() always returns a non-empty string.
Bug: os.environ.get("INJECT_ID") or _DEFAULT_INJECT_USER_ID can return falsy
     when INJECT_ID is unset AND _DEFAULT_INJECT_USER_ID is falsy.
"""

import sys
import os

# Add repo root to sys.path so that 'src' and 'config' are importable
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + "/../..")

# Ensure INJECT_ID is NOT set in the environment
os.environ.pop("INJECT_ID", None)

# Import the module via its public entry point
import src.llm_client as llm_client

try:
    # Monkey-patch _DEFAULT_INJECT_USER_ID to an empty string to trigger the bug
    llm_client._DEFAULT_INJECT_USER_ID = ""

    actual = llm_client._stable_user_id()
    # Spec requires: "The returned string is non-empty in all cases"
    # Bug is triggered if the return is falsy (empty string or None)
    bug_triggered = not actual

except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)

if bug_triggered:
    print(f"CONFIRMED — actual: {actual!r} | expected: non-empty string per spec")
else:
    print(f"NOT CONFIRMED — actual matched expected: {actual!r}")

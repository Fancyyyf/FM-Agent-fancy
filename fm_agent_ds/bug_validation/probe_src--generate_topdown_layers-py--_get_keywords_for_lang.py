"""Probe script: verify _get_keywords_for_lang returns non-empty set per spec.

Bug: When _COMMON_EXTRA_KEYWORDS is empty and lang_key has no configured
keywords, the returned set is empty, violating the spec's guarantee of a
non-empty return value.

Test: Temporarily clear _COMMON_EXTRA_KEYWORDS, call with unknown lang_key,
and check if the result is empty.

Run from repo root: python3 fm_agent/bug_validation/probe_src--generate_topdown_layers-py--_get_keywords_for_lang.py
"""

import sys
import os

# Ensure repo root is on sys.path for the 'src' package import
repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

try:
    import src.generate_topdown_layers as gtl

    # Save original state
    original_extra_keywords = gtl._COMMON_EXTRA_KEYWORDS

    # Clear the cross-language keywords to trigger the latent bug
    gtl._COMMON_EXTRA_KEYWORDS = set()

    # Call with a lang_key that has no entry in LANG_CONFIG
    actual = gtl._get_keywords_for_lang("nonexistent_language")

    # Restore original state
    gtl._COMMON_EXTRA_KEYWORDS = original_extra_keywords

    # Spec claim: returned value is always a non-empty set
    # Actual behavior when both sources are empty: returns empty set
    passed = len(actual) == 0  # Bug reproduced if actual is empty

    if passed:
        print(f"CONFIRMED — actual: {actual!r} (empty set) | expected: non-empty set")
    else:
        print(f"NOT CONFIRMED — actual matched expected (non-empty): {actual!r}")

except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)

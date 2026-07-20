import sys
import os

# Ensure we import from the repo root
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + "/../..")

try:
    import src.generate_topdown_layers as gtl

    # Simulate the trigger condition: make _COMMON_EXTRA_KEYWORDS empty
    original = gtl._COMMON_EXTRA_KEYWORDS
    gtl._COMMON_EXTRA_KEYWORDS = set()

    # Call with an unknown language key (not in LANG_CONFIG)
    # When both _COMMON_EXTRA_KEYWORDS and lang-specific keywords are empty,
    # the result should be empty — violating the spec's non-empty requirement.
    result = gtl._get_keywords_for_lang("unknown_lang")

    # Restore original
    gtl._COMMON_EXTRA_KEYWORDS = original

    # Spec claim: "Returns a non-empty set of strings"
    # If result is empty, the bug is confirmed
    if len(result) == 0:
        print("CONFIRMED — result is empty set, violating spec requirement for non-empty set")
    else:
        print(f"NOT CONFIRMED — result is non-empty: {result!r}")

except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)

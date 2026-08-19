import sys
import os

# Ensure repo root is on path so we can import the source module
repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

try:
    from src.parser import format_info_for_reasoner, FunctionSpecMap

    # Two callees with the same name "foo" but different specs/signatures.
    # Spec claims one entry per callee, but dict-based FunctionSpecMap
    # overwrites duplicate names, keeping only the last one.
    info = {
        "callees": [
            {
                "name": "foo",
                "signature": "def foo(x: int) -> int",
                "pre_condition": "x > 0",
                "post_condition": "returns x + 1",
            },
            {
                "name": "foo",
                "signature": "def foo(x: str) -> str",
                "pre_condition": "x is not empty",
                "post_condition": "returns x.upper()",
            },
        ]
    }

    result = format_info_for_reasoner(info)

    # Expected (spec-correct): 2 entries — one per callee
    # Actual (buggy): only 1 entry because second "foo" overwrites first
    expected_entries = 2
    actual_entries = len(result)

    # Also verify: the retained spec should be from the LAST callee (overwrite),
    # which should be the second one if the bug exists as described.
    retained_spec = result.get("foo", "")
    second_callee_spec_expected = (
        "Pre-condition: x is not empty\n"
        "Post-condition: returns x.upper()"
    )
    first_callee_spec_expected = (
        "Pre-condition: x > 0\n"
        "Post-condition: returns x + 1"
    )

    entry_count_mismatch = actual_entries != expected_entries
    last_overwrites = retained_spec == second_callee_spec_expected

    passed = entry_count_mismatch and last_overwrites

except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)

if passed:
    print(
        f"CONFIRMED — actual entries: {actual_entries!r} (only last callee survives)"
        f" | expected entries: {expected_entries!r} (one per callee)"
    )
    print(f"  retained spec is from callee #2: {retained_spec!r}")
else:
    if not entry_count_mismatch:
        print(
            f"NOT CONFIRMED — entry count matched expected: {actual_entries!r}"
        )
    else:
        print(
            f"NOT CONFIRMED — entry count mismatch ({actual_entries} vs {expected_entries})"
            f" but retained spec does not match callee #2: {retained_spec!r}"
        )

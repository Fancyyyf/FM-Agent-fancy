"""Probe script for bug: _safe_staged_name — underscore before numeric suffix."""

import sys

try:
    from src.domain_knowledge import _safe_staged_name

    # Trigger: base candidate "test.txt" already in used_names → disambiguation path
    source_path = "/some/absolute/path/to/test.txt"
    used_names = {"test.txt"}

    actual = _safe_staged_name(source_path, used_names)

    # Spec says: "numeric suffix is appended" → should be "test2.txt"
    # Buggy code produces: "test_2.txt" (underscore before number)
    expected_spec = "test2.txt"
    expected_buggy = "test_2.txt"

    if actual == expected_buggy:
        print(
            f"CONFIRMED — actual: {actual!r} | spec-expected: {expected_spec!r}"
        )
    elif actual == expected_spec:
        print(
            f"NOT CONFIRMED — actual matched spec: {actual!r}"
        )
    else:
        print(
            f"NOT CONFIRMED — unexpected actual: {actual!r}"
            f" | spec-expected: {expected_spec!r}"
            f" | buggy-expected: {expected_buggy!r}"
        )

except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)

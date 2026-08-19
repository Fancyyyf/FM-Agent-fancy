"""Probe script for _optional_string bug: isinstance vs type check for str subclasses."""

import sys
import os

# Allow importing from the repo root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

try:
    from src.call_graph_edges import _optional_string

    class MyString(str):
        """A trivial subclass of str used to test the isinstance vs type check."""
        pass

    # A str subclass instance should trigger ValueError per spec ("not of type str"),
    # but the code uses isinstance() which accepts subclasses.
    value = MyString("hello")

    try:
        result = _optional_string(value, "test_key", "test_source")
        # If we get here, no ValueError was raised — the bug is confirmed.
        # Spec says it should raise ValueError for non-exact-str types.
        expected_error_msg = "test_source: 'test_key' must be a string"
        print(
            "CONFIRMED — isinstance() accepted str subclass, "
            f"but spec requires exact type() check. "
            f"Returned: {result!r}"
        )
    except ValueError:
        # If ValueError IS raised, the code matches the spec — bug not confirmed.
        print(
            "NOT CONFIRMED — ValueError raised for str subclass, "
            "which matches the spec requirement"
        )
except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)

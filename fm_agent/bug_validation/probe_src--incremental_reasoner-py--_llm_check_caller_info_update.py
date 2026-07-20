import sys
import os

# Add the project root to sys.path so 'config' and 'src' package are importable.
_snapshot_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _snapshot_root)

try:
    # Import via the public 'src' package entry point.
    from src.incremental_reasoner import _validate_caller_info_update

    # The specification requires that when info_updated is True, new_info must be the
    # complete replacement [INFO] block with markers, all entries for other callees
    # preserved byte-for-byte, and only the named callee's entry adjusted.
    #
    # _validate_caller_info_update only checks that new_info is a non-empty string --
    # it does not verify any of these semantic constraints. So a well-typed response
    # with arbitrary content passes validation.
    data = {"info_updated": True, "new_info": "arbitrary garbage, not a valid [INFO] block"}

    # According to the spec, this call SHOULD raise ValueError because new_info
    # does not contain a valid [INFO] block. Instead, the validator accepts it.
    result = _validate_caller_info_update(data)

    # Bug reproduced: the validator returned successfully instead of rejecting the input.
    expected = "ValueError raised — new_info must be a complete [INFO] block"
    actual = result
    print(f"CONFIRMED — actual: {actual!r} | expected: {expected!r}")

except ValueError:
    # If the validator did raise ValueError, the bug is NOT confirmed --
    # the validator enforces semantic constraints correctly.
    print("NOT CONFIRMED — validator correctly rejected invalid new_info content")
except ImportError:
    # Module-level imports (config, openai, etc.) may fail in this environment.
    # Fall back to testing the validator logic in isolation (verbatim copy from source).

    # The validator function (copied verbatim from src/incremental_reasoner.py:931-945)
    def _validate_caller_info_update(data):
        """Validate a direct LLM decision about one caller's [INFO] block."""
        if not isinstance(data, dict):
            raise ValueError("caller-info JSON must be an object")
        required = ("info_updated", "new_info")
        missing = [field for field in required if field not in data]
        if missing:
            raise ValueError("caller-info JSON missing required field(s): " + ", ".join(missing))
        if not isinstance(data["info_updated"], bool):
            raise ValueError("caller-info JSON field info_updated must be a boolean")
        if not isinstance(data["new_info"], str):
            raise ValueError("caller-info JSON field new_info must be a string")
        if data["info_updated"] and not data["new_info"].strip():
            raise ValueError("caller-info JSON requires non-empty new_info when info_updated is true")
        return {"info_updated": data["info_updated"], "new_info": data["new_info"].strip()}

    data = {"info_updated": True, "new_info": "arbitrary garbage, not a valid [INFO] block"}
    try:
        result = _validate_caller_info_update(data)
        expected = "ValueError raised — new_info must be a complete [INFO] block"
        print(f"CONFIRMED — actual: {result!r} | expected: {expected!r}")
    except ValueError:
        print("NOT CONFIRMED — validator correctly rejected invalid new_info content")

except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)

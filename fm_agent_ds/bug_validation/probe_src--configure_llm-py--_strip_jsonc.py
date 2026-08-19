"""Probe script for _strip_jsonc bug: newlines inside block comments leak into output."""

import sys
import os

# The probe must work from the repo root. Ensure we can import the module.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + "/../..")

try:
    from src.configure_llm import parse_existing_opencode_config, ConfigWizardError

    # Test input: block comment with a newline inside it sits between two number
    # tokens ("12" and "34") that must merge into "1234" when the comment is
    # removed.  If the newline leaks, "12\n34" is two tokens, which is invalid
    # JSON inside the object value position → json.loads fails.
    test_input = '{"a": 12/* comment\n*/34}'

    # Expected: comment stripped → '{"a": 1234}' → json.loads → {"a": 1234}
    actual = None
    try:
        actual = parse_existing_opencode_config(test_input)
        # If we reach here, json.loads succeeded
        # The buggy code would have caused a ConfigWizardError / JSONDecodeError
        # But if the bug is present and the newline leaks, we get:
        #   '{"a": 12\n34}' → json.loads fails → ConfigWizardError raised
        # Since we DIDN'T get an error, let's check whether this is actually
        # testing the right thing...
        #
        # Actually, we need a case where the buggy code produces a different
        # result.  Let's also directly test _strip_jsonc to confirm the leakage.
    except ConfigWizardError:
        # Bug confirmed: a valid JSONC input (after proper comment removal)
        # fails to parse because the leaked newline breaks the JSON structure.
        pass
    except Exception as exc:
        print(f'ERROR: unexpected exception: {type(exc).__name__}: {exc}')
        sys.exit(1)

    # --- Direct test of _strip_jsonc for unambiguous confirmation ---
    from src.configure_llm import _strip_jsonc

    simple_input = "/* a\n*/b"
    actual_result = _strip_jsonc(simple_input)
    expected_result = "b"

    buggy_result = "\nb"  # what the buggy code produces

    if actual_result == expected_result:
        print(f"NOT CONFIRMED — direct _strip_jsonc test: actual={actual_result!r} matched expected={expected_result!r}")
    elif actual_result == buggy_result:
        print(f"CONFIRMED — _strip_jsonc leaked newline inside block comment: actual={actual_result!r} | expected={expected_result!r}")
    else:
        print(f"NOT CONFIRMED — unexpected result: actual={actual_result!r} | expected={expected_result!r}")

except ImportError as exc:
    print(f"ERROR: import failed: {exc}")
    sys.exit(1)

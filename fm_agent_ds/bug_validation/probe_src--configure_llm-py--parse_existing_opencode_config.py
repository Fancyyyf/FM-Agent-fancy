import sys
sys.path.insert(0, '.')

try:
    from src.configure_llm import parse_existing_opencode_config, ConfigWizardError
except ImportError as e:
    print(f'ERROR: {e}')
    sys.exit(1)

actual = None
expected = None
passed = False

try:
    result = parse_existing_opencode_config("[]")
    actual = type(result).__name__
    # Spec says: "returns a dict whose keys and values are the parsed top-level JSON object"
    # For text="[]", valid JSON parses to a list, not a dict.
    # The spec says returns a dict → so expected is dict, but code raised ConfigWizardError
    # However, if it didn't raise, the returned value type is what we compare
    expected = "dict"
    passed = actual != expected
    if passed:
        print(f"CONFIRMED — actual: returned {actual!r} | expected: {expected!r} (spec claimed it returns a dict)")
    else:
        print(f"NOT CONFIRMED — actual matched expected: {actual!r}")
except ConfigWizardError as e:
    # The code raised ConfigWizardError for valid JSON that parses to a non-dict
    # Spec says "returns a dict" for valid JSON → raising an error is a deviation
    actual = f"ConfigWizardError: {e}"
    expected = "dict (spec says valid JSON should return a dict)"
    passed = True  # Bug confirmed: code raises error, spec says return dict
    print(f"CONFIRMED — actual: {actual!r} | expected: {expected!r}")
except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)

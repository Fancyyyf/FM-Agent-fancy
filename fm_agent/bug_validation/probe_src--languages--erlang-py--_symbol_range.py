import sys
import os

# Add workspace root to path so `src` is importable
_workspace = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _workspace not in sys.path:
    sys.path.insert(0, _workspace)

try:
    from src.languages.erlang import _symbol_range

    # Trigger condition: 'location' is truthy but not a dict (e.g., a string)
    # Expected (spec-correct): returns None
    # Actual (buggy): raises AttributeError because string has no .get() method
    symbol = {"location": "some/path.erl"}

    try:
        actual = _symbol_range(symbol)
        # If we reach here, no exception was raised
        expected = None  # spec says should return None when location has no 'range'
        passed = actual != expected
        if passed:
            print(f"CONFIRMED — actual: {actual!r} | expected: {expected!r}")
        else:
            print(f"NOT CONFIRMED — actual matched expected: {actual!r}")
    except AttributeError as e:
        # Bug reproduced: spec says return None, but we got AttributeError
        print(f"CONFIRMED — AttributeError raised: {e} | expected: None (no range found)")
    except Exception as e:
        print(f"ERROR: unexpected exception type {type(e).__name__}: {e}")
        sys.exit(1)

except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)

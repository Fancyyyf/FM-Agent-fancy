import sys
import os

# Add the repo root to sys.path so we can import the package
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + "/../..")

try:
    import config
    from src.llm_client import _stable_user_id

    # Store original value and set inject.id to a non-string truthy value (integer)
    original_id = config.settings.inject.id
    config.settings.inject.id = 5  # truthy non-string → or returns this instead of the default

    actual = _stable_user_id()

    # Restore original value
    config.settings.inject.id = original_id

    # Bug is confirmed if _stable_user_id returned a non-string value
    # The spec requires it to always return a string, but `or` returns the
    # first truthy operand as-is — so when inject.id is a truthy non-string,
    # the function returns that non-string value.
    passed = not isinstance(actual, str)

except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)

if passed:
    print(f'CONFIRMED — actual type: {type(actual).__name__}, value: {actual!r} | expected type: str')
else:
    print(f'NOT CONFIRMED — actual is string: {actual!r}')

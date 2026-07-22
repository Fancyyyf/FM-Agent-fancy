import sys
import os

# Ensure repo root is on sys.path so `from config import settings` resolves
repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

try:
    from config import settings
    from src.cli_backend import cli_effort

    # Store original value to restore later
    original = settings.llm.effort

    # Monkey-patch settings.llm.effort with a bytes value (bypassing pydantic validation)
    object.__setattr__(settings.llm, 'effort', b'  hello  ')

    actual = cli_effort()
    expected = 'hello'  # Per spec: should return stripped string

    # Restore original
    object.__setattr__(settings.llm, 'effort', original)

    # Bug confirmed if actual is bytes (not str) — the function failed to ensure str return
    is_bytes = isinstance(actual, bytes)
    is_str = isinstance(actual, str)

    if is_bytes:
        print(f'CONFIRMED — actual: {actual!r} (type: {type(actual).__name__}) | expected str: {expected!r}')
    elif is_str:
        print(f'NOT CONFIRMED — actual matched expected str: {actual!r}')
    else:
        print(f'CONFIRMED — actual type {type(actual).__name__} is neither str nor bytes: {actual!r}')

except Exception as e:
    print(f'ERROR: {e}', file=sys.stderr)
    sys.exit(1)

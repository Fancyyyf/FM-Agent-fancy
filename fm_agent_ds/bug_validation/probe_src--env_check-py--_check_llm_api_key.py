import sys
import os

# Ensure the repo root is on sys.path so that `src` is importable
_repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

class MockConfig:
    """Minimal config-like object exposing LLM_API_KEY as an attribute."""
    def __init__(self, api_key):
        self.LLM_API_KEY = api_key

try:
    from src.env_check import _check_llm_api_key

    # Test: whitespace-only API key should be rejected after stripping
    config = MockConfig("   ")
    ok, msg = _check_llm_api_key(config)

    actual = (ok, msg)
    # Spec says: strip whitespace → key becomes "" → in placeholders → (False, error_msg)
    expected = (False, "LLM_API_KEY is not set in .env file")
    # Bug is confirmed if actual != expected (actual erroneously returns True)
    passed = actual != expected

    if passed:
        print(f'CONFIRMED — actual: {actual!r} | expected: {expected!r}')
    else:
        print(f'NOT CONFIRMED — actual matched expected: {actual!r}')

except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)

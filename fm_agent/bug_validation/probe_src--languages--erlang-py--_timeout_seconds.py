import os
import sys

# Run from repo root; ensure the repo root is on sys.path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

try:
    from config import settings
    from src.languages.erlang import _timeout_seconds

    _DEFAULT_TIMEOUT_SECONDS = 180

    # Ensure ELP_TIMEOUT_SECONDS is NOT in the environment
    os.environ.pop("ELP_TIMEOUT_SECONDS", None)

    # Modify settings to diverge from the default constant.
    # The spec says: when ELP_TIMEOUT_SECONDS is not set → return _DEFAULT_TIMEOUT_SECONDS.
    # The code reads settings.erlang.timeout_s, so changing it to a non-default
    # value should NOT affect the output — but it does.
    settings.erlang.timeout_s = 30

    actual = _timeout_seconds()
    expected = _DEFAULT_TIMEOUT_SECONDS  # spec-required fallback

    passed = actual != expected

except Exception as e:
    print(f"ERROR: {type(e).__name__}: {e}")
    sys.exit(1)

if passed:
    print(f"CONFIRMED — actual: {actual!r} | expected: {expected!r}")
else:
    print(f"NOT CONFIRMED — actual matched expected: {actual!r}")

import sys
import os

# Ensure we import from the repo root (cwd for the probe runner).
sys.path.insert(0, os.getcwd())

try:
    import config
    from src.llm_client import _stable_user_id
except Exception as e:
    print(f"ERROR: import failed — {e}")
    sys.exit(1)

try:
    # Record initial state
    saved_id = config.settings.inject.id

    # First call: settings.inject.id defaults to "" (empty),
    # so _stable_user_id() should return _DEFAULT_INJECT_USER_ID.
    first = _stable_user_id()

    # Change settings.inject.id to a different value.
    config.settings.inject.id = "altered-user-999"

    # Second call: should now return the new value, NOT the original.
    second = _stable_user_id()

    # Restore original setting to keep the environment clean.
    config.settings.inject.id = saved_id

    # spec says: "stable — repeated calls within the same execution
    # environment yield the same string"
    # If first != second, the bug is confirmed.
    if first != second:
        print(
            f"CONFIRMED — first: {first!r} | second: {second!r} "
            f"| setting changed from {saved_id!r} to 'altered-user-999'"
        )
    else:
        print(
            f"NOT CONFIRMED — first: {first!r} | second: {second!r} "
            f"| values matched (function is stable)"
        )
except Exception as e:
    print(f"ERROR: {type(e).__name__}: {e}")
    sys.exit(1)

"""Probe script for bug: _matches_inject_target only treats http:// and https://
as absolute URL prefixes; other schemes (e.g., ftp://) incorrectly fall through
to hostname matching."""

import sys
import os

# Allow imports from the repo root (package entry point).
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

try:
    # Set target to an ftp:// URL prefix via INJECT_HOST so _inject_targets()
    # picks it up, then exercise _matches_inject_target through the smallest
    # public wrapper: _should_inject_user_id.
    os.environ["INJECT_HOST"] = "ftp://example.com/"
    from src.llm_client import _should_inject_user_id

    actual = _should_inject_user_id("ftp://example.com/file")
    # Specification requires True: the url begins with the absolute URL prefix target.
    expected = True
    passed = actual != expected
except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)

if passed:
    print(f"CONFIRMED — actual: {actual!r} | expected: {expected!r}")
else:
    print(f"NOT CONFIRMED — actual matched expected: {actual!r}")

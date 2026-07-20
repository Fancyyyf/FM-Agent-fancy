"""Probe script for bug: _ContentModifiedError.__init__ uses str(error) instead of error message."""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))
sys.path.insert(0, "src")

try:
    from languages.erlang import _ContentModifiedError
except ImportError:
    sys.path.insert(0, os.path.abspath("src"))
    from languages.erlang import _ContentModifiedError

try:
    error_dict = {"code": -32800, "message": "Requested resource has been modified"}
    exc = _ContentModifiedError(error_dict)
    actual = str(exc)
    # Spec-correct expected: the human-readable message field from the error dict
    expected = error_dict.get("message", str(error_dict))

    # Bug: str(exc) == str(error_dict) (full dict repr), not the message field
    # The bug exists when actual (Python repr of dict) differs from expected (message field)
    passed = actual != expected

    if passed:
        print(f"CONFIRMED — actual: {actual!r} | expected (message field): {expected!r}")
    else:
        print(f"NOT CONFIRMED — actual matched expected: {actual!r}")
except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)

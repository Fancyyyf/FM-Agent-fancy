"""Probe script for bug: src--languages--cpp-py--function_spans

Bug: function_spans() does not handle exceptions from CodeGraphExtractor.from_proj_dir().
The specification requires returning None when the codegraph backend is unavailable,
but exceptions propagate instead of being caught.

Trigger: proj_dir=None causes os.path.abspath(None) in from_proj_dir() to raise TypeError.
"""

import sys
import os

# Ensure the repo root is on sys.path so src.languages.cpp is importable
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

try:
    from src.languages.cpp import function_spans
except ImportError as e:
    print(f"ERROR: Could not import function_spans: {e}")
    sys.exit(1)

# --- Test: proj_dir=None should cause an exception that the spec says must be caught ---
error_caught = None
actual = None

try:
    actual = function_spans(None, "dummy.cpp")
except TypeError as e:
    error_caught = f"TypeError: {e}"
except Exception as e:
    error_caught = f"{type(e).__name__}: {e}"

expected = None  # Spec: "Returns None when a codegraph backend is unavailable"

if error_caught is not None:
    # Exception propagated → bug confirmed (spec says return None, not raise)
    print(f"CONFIRMED — exception propagated: {error_caught} | expected: {expected!r}")
elif actual == expected:
    print(f"NOT CONFIRMED — actual matched expected: {actual!r}")
else:
    print(f"CONFIRMED — actual: {actual!r} | expected: {expected!r}")

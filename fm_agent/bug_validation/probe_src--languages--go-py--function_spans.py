"""Probe script for bug ID: src--languages--go-py--function_spans.

Tests whether function_spans returns None (spec-correct) or propagates an
exception (buggy) when CodeGraphExtractor.from_proj_dir raises.
"""
import sys
import os

# Ensure the project root is on sys.path so that `src` is importable.
_project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

try:
    from src.languages.go import function_spans
except ImportError as e:
    print(f'ERROR: Could not import src.languages.go: {e}')
    sys.exit(1)

actual = sentinel = object()
passed = False

# Attempt 1: Pass None as proj_dir to trigger os.path.abspath(None) -> TypeError
# inside CodeGraphExtractor.from_proj_dir. The spec requires function_spans to
# return None when the backend is unavailable, not to propagate exceptions.
try:
    actual = function_spans(None, "some_file.go")
except TypeError:
    # Bug confirmed: exception propagated instead of returning None
    passed = True
    actual = '<TypeError raised>'
except Exception as e:
    # Some other exception propagated — also a bug
    passed = True
    actual = f'<{type(e).__name__} raised: {e}>'
else:
    # No exception — function returned a value
    # The spec says it should return None when backend is unavailable
    if actual is not None:
        # Bug: returned something other than None despite backend failure
        passed = True

expected = 'None (spec-correct)'

if passed:
    print(f'CONFIRMED — actual: {actual!r} | expected: {expected!r}')
else:
    print(f'NOT CONFIRMED — actual matched expected: {actual!r}')

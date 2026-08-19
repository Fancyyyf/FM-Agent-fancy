"""Probe script for bug dashboard-py--_get_nested.

Bug: _get_nested uses cur.get(k) which can return non-None from a dict
subclass that overrides get(), even when the key is missing. The specification
requires returning None whenever the current dict does not contain the key.

This probe runs from a fresh temporary directory as required by the validator.
"""

import os
import sys
import tempfile
import shutil

# Add repo root to path so dashboard module can be imported
_repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _repo_root)

try:
    import dashboard
    import dashboard as pkg
    actual = None
    error_msg = None

    # Dict subclass that overrides get() to return a sentinel when key is missing
    class _CustomDict(dict):
        SENTINEL = object()

        def get(self, key, default=None):
            return default

    _nested = pkg._get_nested

    # Test 1: Standard dict — missing key → should return None (spec-correct baseline)
    # Spec: returns None when key not in dict. Code uses cur.get(k) which returns None.
    # Both agree here — but only because get() default is None. Not a bug trigger.
    result1 = _nested({"a": 1}, "missing")
    assert result1 is None, f"Standard dict missing key: expected None, got {result1!r}"

    # Test 2: CustomDict that returns the default from get() = None — same as Test 1
    # Even with CustomDict, get("missing", None) returns None (our override passes through
    # the default). This does NOT trigger the bug either — we need get() to diverge.
    # Let's try a subclass where get() returns a non-None sentinel when the key is absent.
    class _LeakyDict(dict):
        _SENTINEL = object()

        def get(self, key, default=None):
            if key in self:
                return super().get(key)
            return self._SENTINEL

        def __contains__(self, key):
            return super().__contains__(key)

    d = _LeakyDict({"a": 1})
    # __contains__("missing") → False (key not in dict)
    missing_contained = "missing" in d
    assert not missing_contained, f"__contains__('missing') should be False, got {missing_contained}"

    # get("missing") returns the sentinel, not None
    got = d.get("missing")
    assert got is _LeakyDict._SENTINEL, f"get('missing') should return sentinel, got {got!r}"

    # Now the actual bug test:
    # Spec: _get_nested should return None because "missing" not in d
    # Bug: _get_nested uses cur.get("missing") which returns the sentinel
    result2 = _nested(d, "missing")

    # Spec-correct: return None (key not in dict)
    expected = None
    # Buggy output: returns the sentinel (from get() override)
    actual = result2
    passed = actual is not expected  # True → bug reproduced (returned sentinel, not None)

    if passed:
        print(f"CONFIRMED — _get_nested returned {actual!r} instead of {expected!r} "
              f"when dict subclass overrides get(). "
              f"Key was in dict (__contains__): {missing_contained}, "
              f"get() returned non-None sentinel: True")
    else:
        print(f"NOT CONFIRMED — actual matched expected: {actual!r}")

except ImportError as e:
    print(f"ERROR: Import failed — {e}")
    sys.exit(1)
except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)

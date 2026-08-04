"""Probe for _qualified_parts bug: code strips whitespace from qualified_name
before checking endswith(name), while the spec requires checking the raw
qualified_name. For input '   Foo::bar   ' with name='bar', the spec says
the raw string does NOT end with 'bar', so the result should be ['bar'];
the buggy code strips first, finds it ends with 'bar', and returns ['Foo', 'bar'].
"""

import os
import sys
import tempfile

# Ensure the repo root is importable
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

# Create a fresh temporary directory for the probe workspace
# (as required by FM-Agent self-validation guard)
_probe_workspace = tempfile.mkdtemp(prefix="qualified_parts_probe_")

try:
    from src.languages.codegraph import _qualified_parts

    # Trigger condition: qualified_name with leading/trailing whitespace.
    # The raw string "   Foo::bar   " does NOT end with "bar" (it ends with "   "),
    # so per spec the result should be [name] = ["bar"].
    # The buggy code strips whitespace first, yielding "Foo::bar" which DOES
    # end with "bar", producing ["Foo", "bar"] instead.
    name = "bar"
    qualified_name = "   Foo::bar   "

    actual = _qualified_parts(name, qualified_name)

    # Spec-correct expectation: raw qualified_name does not end with name
    expected = ["bar"]

    passed = actual != expected

    if passed:
        print(
            f"CONFIRMED — actual: {actual!r} | expected: {expected!r} "
            f"(code strips whitespace before endswith check, "
            f"spec requires checking raw qualified_name)"
        )
    else:
        print(f"NOT CONFIRMED — actual matched expected: {actual!r}")

except ImportError as e:
    import traceback

    traceback.print_exc()
    print(f"ERROR: Cannot import _qualified_parts: {e}")
    sys.exit(1)
except Exception:
    import traceback

    traceback.print_exc()
    print("ERROR: probe script failed with an unhandled exception")
    sys.exit(1)
finally:
    # Cleanup probe workspace
    try:
        os.rmdir(_probe_workspace)
    except OSError:
        pass

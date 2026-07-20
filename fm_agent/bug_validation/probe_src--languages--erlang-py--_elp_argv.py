"""Probe script for _elp_argv bug: shlex.split raises ValueError on unbalanced quoting."""
import os
import sys
import traceback

# Ensure the project root is on sys.path so the public entry-point import works
_project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

# Set ELP_COMMAND to a value with unbalanced quoting that triggers shlex.split ValueError
os.environ["ELP_COMMAND"] = '"unclosed'

try:
    from src.languages.erlang import _elp_argv

    actual = _elp_argv()
    if isinstance(actual, list) and len(actual) > 0:
        print(f"NOT CONFIRMED — function returned list: {actual!r}")
    else:
        print(f"CONFIRMED — function returned non-list or empty: {actual!r}")

except ValueError:
    # Spec: function must return a non-empty list of strings.
    # Actual: shlex.split raises ValueError on unbalanced quoting.
    print("CONFIRMED — shlex.split raised ValueError on unbalanced quoting (spec requires non-empty list)")
except Exception as e:
    print(f"ERROR: {e}")
    traceback.print_exc()
    sys.exit(1)

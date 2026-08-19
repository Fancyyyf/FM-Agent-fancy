import sys
import os
import json
import tempfile

# Ensure the repo root is on sys.path for package import
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

try:
    from src.parser import parse_input_function, format_spec_for_reasoner
except Exception as e:
    print(f"ERROR: Could not import src.parser: {e}")
    sys.exit(1)

try:
    # Create a temporary directory for test fixtures
    with tempfile.TemporaryDirectory() as tmpdir:
        source_path = os.path.join(tmpdir, "test_func.py")
        spec_path = source_path + ".spec.json"

        # Write a minimal source file
        with open(source_path, "w") as f:
            f.write("def foo():\n    return 42\n")

        # Write an empty .spec.json — file exists and parses, but yields {}
        with open(spec_path, "w") as f:
            f.write("{}")

        # Call the function under test via public entry point
        func, nl_spec, knowledge = parse_input_function(source_path)

        # Expected behavior per spec: sidecar present and loadable, so
        # format_spec_for_reasoner should be called with {}
        expected = format_spec_for_reasoner({})

        # Bug check: if nl_spec is empty string but expected is not, bug confirmed
        passed = (nl_spec != expected)

        if passed:
            print(f"CONFIRMED — actual (buggy) nl_spec: {nl_spec!r} | expected (spec-correct): {expected!r}")
        else:
            print(f"NOT CONFIRMED — actual nl_spec matches expected: {nl_spec!r}")
except Exception as e:
    import traceback
    print(f"ERROR: {e}")
    traceback.print_exc()
    sys.exit(1)

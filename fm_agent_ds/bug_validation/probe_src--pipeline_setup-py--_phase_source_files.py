"""Probe: _phase_source_files should exclude non-integer phase values.

Bug: The function only checks for None, so a string phase like 'abc' is included
in the returned dictionary, violating the spec that says non-integer values
must be excluded.
"""

import sys
import json
import os
import tempfile

# Ensure the repo root is on the Python path so 'src' can be found.
_script_dir = os.path.dirname(os.path.abspath(__file__))
_repo_root = os.path.dirname(os.path.dirname(_script_dir))  # up two levels
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)


def run_probe():
    # Create a temporary phases.json with a non-integer phase value.
    with tempfile.TemporaryDirectory() as tmpdir:
        phases_json_path = os.path.join(tmpdir, "phases.json")
        phases_data = {
            "phases": [
                {
                    "phase": 1,
                    "name": "Valid Phase",
                    "modules": [
                        {
                            "name": "mod_a",
                            "source_files": ["src/a.py"]
                        }
                    ]
                },
                {
                    "phase": "abc",  # Non-integer phase — spec says exclude
                    "name": "String Phase",
                    "modules": [
                        {
                            "name": "mod_b",
                            "source_files": ["src/b.py"]
                        }
                    ]
                }
            ]
        }
        with open(phases_json_path, "w") as f:
            json.dump(phases_data, f)

        # Import the function from the package module.
        from src.pipeline_setup import _phase_source_files

        result = _phase_source_files(phases_json_path)

        # Check results
        actual_keys = list(result.keys())
        has_string_key = any(isinstance(k, str) for k in actual_keys)
        has_int_key = any(isinstance(k, int) for k in actual_keys)

        if has_string_key and "abc" in result:
            actual = dict(result)  # for display
            expected = {1: ["src/a.py"]}  # spec: only integer phases
            passed = actual != expected
            print(
                f"CONFIRMED — Non-integer phase key 'abc' present in result. "
                f"actual: {actual!r} | expected: {expected!r}"
            )
        elif not has_string_key:
            print(
                f"NOT CONFIRMED — Non-integer phase was correctly excluded. "
                f"actual keys: {actual_keys!r}"
            )
        else:
            print(
                f"NOT CONFIRMED — Unexpected result: {result!r}"
            )


if __name__ == "__main__":
    try:
        run_probe()
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

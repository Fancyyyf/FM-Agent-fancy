"""Probe script for bug: _deduplicate_phases incorrectly deduplicates
files within the same module.

The spec: deduplication should only remove files that appear in MULTIPLE
modules. Within a single module, duplicate entries should be preserved.

The bug: the global `seen` set tracks ALL seen files, so if a file appears
twice in the same module's source_files, the second occurrence gets removed.
"""
import sys
import os
import json
import tempfile

# Import via the public entry point (src package)
from src.pipeline_setup import _deduplicate_phases

def test():
    # Create a temp directory with a phases.json containing a module
    # that lists the same source file twice in its source_files list.
    with tempfile.TemporaryDirectory() as tmpdir:
        phases_json_path = os.path.join(tmpdir, "phases.json")

        # Input: one phase, one module, "a.py" appears TWICE in source_files
        input_data = {
            "phases": [
                {
                    "phase": 1,
                    "modules": [
                        {
                            "name": "module_foo",
                            "source_files": ["a.py", "b.py", "a.py"]
                        }
                    ]
                }
            ]
        }

        with open(phases_json_path, "w") as f:
            json.dump(input_data, f)

        # Call the function under test
        result = _deduplicate_phases(tmpdir)

        # Read back the modified phases.json
        with open(phases_json_path, "r") as f:
            output_data = json.load(f)

        output_files = output_data["phases"][0]["modules"][0]["source_files"]

        # Spec says: dedup only across modules, not within the same module.
        # "a.py" appears twice in ONE module → should be preserved (both copies).
        # Expected: ["a.py", "b.py", "a.py"] — unchanged
        # Actual (buggy): ["a.py", "b.py"] — second "a.py" removed
        expected = ["a.py", "b.py", "a.py"]
        actual = output_files

        # The bug is confirmed if actual != expected
        if actual != expected:
            print(f"CONFIRMED — actual: {actual!r} | expected: {expected!r}")
            print(f"modified_modules: {result.get('modified_modules')!r}")
        else:
            print(f"NOT CONFIRMED — actual matched expected: {actual!r}")

if __name__ == "__main__":
    try:
        test()
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

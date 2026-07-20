import sys
import os
import json
import tempfile
import shutil

try:
    from src.pipeline_setup import _collapse_phases_to_one
except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)

# Create a temporary work directory with phases.json where first phase number is NOT 1
tmp_dir = tempfile.mkdtemp(prefix="bug_probe_")

# phases.json with first phase number = 3 (not 1)
phases_json = {
    "phases": [
        {
            "phase": 3,
            "name": "Phase Three",
            "description": "Third phase description",
            "modules": ["mod_a.py", "mod_b.py"],
            "depends_on_phases": [1, 2]
        },
        {
            "phase": 5,
            "name": "Phase Five",
            "description": "Fifth phase description",
            "modules": ["mod_c.py"],
            "depends_on_phases": [3]
        }
    ]
}

phases_path = os.path.join(tmp_dir, "phases.json")
with open(phases_path, "w") as f:
    json.dump(phases_json, f, indent=2)

try:
    _collapse_phases_to_one(tmp_dir)

    # Read the resulting phases.json
    with open(phases_path) as f:
        result = json.load(f)

    merged_phase = result["phases"][0]
    actual_phase = merged_phase["phase"]

    # Spec says phase must be 1 — buggy code preserves original phase number
    expected_phase = 1

    if actual_phase != expected_phase:
        print(f'CONFIRMED — spec requires phase=1, but code returned phase={actual_phase}')
    else:
        print(f'NOT CONFIRMED — actual phase matched expected: {actual_phase}')

except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)
finally:
    # Cleanup temp directory
    if os.path.isdir(tmp_dir):
        shutil.rmtree(tmp_dir, ignore_errors=True)

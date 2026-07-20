import sys
import json
import os
import tempfile

# Add the repo root to sys.path so 'src' is importable
# Script is at fm_agent/bug_validation/probe_*.py, go up 3 levels to repo root
repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, repo_root)

try:
    from src.pipeline_setup import _ensure_source_files_in_phases
except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)

# Create a temporary phases.json with one phase and one module
tmpdir = tempfile.mkdtemp()
phases_json = os.path.join(tmpdir, "phases.json")

initial_data = {
    "phases": [
        {
            "phase": 1,
            "name": "Test Phase",
            "description": "A test phase.",
            "depends_on_phases": [],
            "modules": [
                {
                    "name": "test_module",
                    "description": "Test module.",
                    "source_files": ["existing_file.py"]
                }
            ]
        }
    ]
}

with open(phases_json, "w") as f:
    json.dump(initial_data, f, indent=2)

# required_source_files with two entries that normalize to the same path
# on Linux both 'path/to/dup.py' and 'path\\to\\dup.py' normalize to 'path/to/dup.py'
required_source_files = ["path/to/dup.py", "path\\to\\dup.py"]

result = _ensure_source_files_in_phases(phases_json, required_source_files)

# Read back the modified phases.json
with open(phases_json, "r") as f:
    modified_data = json.load(f)

# Get the source_files of the first module of the first phase
actual_source_files = modified_data["phases"][0]["modules"][0]["source_files"]
actual_forced = result["forced"]

# Expected (spec-correct): only ONE copy of the normalized path should be added
# since both entries in required_source_files normalize to 'path/to/dup.py'
expected_source_files = ["existing_file.py", "path/to/dup.py"]
expected_forced = ["path/to/dup.py"]

# Check: are there duplicates in the source_files list?
normalized_added = [sf.replace("\\", "/") for sf in actual_source_files]
duplicates_detected = len(normalized_added) != len(set(normalized_added))

# The bug is: both entries end up in source_files and forced
passed = duplicates_detected or len(actual_forced) > 1

# Clean up
os.remove(phases_json)
os.rmdir(tmpdir)

if passed:
    print(f"CONFIRMED — actual source_files: {actual_source_files!r} | expected: {expected_source_files!r}")
    print(f"  forced: {actual_forced!r} (expected max 1 entry)")
else:
    print(f"NOT CONFIRMED — actual matched expected: source_files={actual_source_files!r}, forced={actual_forced!r}")

import sys
import os
import json
import tempfile

# Add repo root to sys.path so the 'src' package + 'config' module resolve.
repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, repo_root)

try:
    from src.pipeline_setup import _ensure_source_files_in_phases
except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)

# Build a temporary phases.json where "foo.py" is duplicated across TWO modules
# of the same phase.  The spec post-condition requires every required source
# file to appear in EXACTLY ONE module, but the implementation collects all
# source files into a flat set and only checks membership, not uniqueness.
tmpdir = tempfile.mkdtemp()
phases_json_path = os.path.join(tmpdir, "phases.json")

initial_phases = {
    "phases": [
        {
            "phase": 1,
            "name": "Phase One",
            "description": "First phase.",
            "modules": [
                {
                    "name": "mod_a",
                    "description": "Module A.",
                    "source_files": ["foo.py", "bar.py"],
                },
                {
                    "name": "mod_b",
                    "description": "Module B.",
                    "source_files": ["foo.py", "baz.py"],
                },
            ],
            "depends_on_phases": [],
        }
    ]
}
with open(phases_json_path, "w") as f:
    json.dump(initial_phases, f)

required_source_files = ["foo.py"]

try:
    result = _ensure_source_files_in_phases(phases_json_path, required_source_files)
except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)

# Re-read phases.json to count how many modules still claim "foo.py".
with open(phases_json_path, "r") as f:
    after = json.load(f)

foo_count = 0
for phase in after["phases"]:
    for module in phase["modules"]:
        if "foo.py" in module.get("source_files", []):
            foo_count += 1

# Bug reproduced when:
#   1) The function returned an empty result (did NOT add or fix anything), AND
#   2) foo.py still appears in more than 1 module.
# The spec requires exactly 1.
forced_empty = result.get("forced") == []
aug_empty = result.get("augmented") == {}
still_duplicated = foo_count > 1

bug_confirmed = forced_empty and aug_empty and still_duplicated

if bug_confirmed:
    print(
        f'CONFIRMED — actual: forced={result["forced"]!r}, foo.py appears in '
        f'{foo_count} modules after call | expected (spec): exactly 1 module'
    )
else:
    print(
        f'NOT CONFIRMED — result={result!r}, foo_count={foo_count}'
    )

# Cleanup temporary directory.
import shutil
shutil.rmtree(tmpdir, ignore_errors=True)

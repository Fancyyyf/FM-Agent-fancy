# [SPEC]
# Unit: src/generate_topdown_layers-py/_load_phases.py
#
# _load_phases(proj_dir: str) -> dict
#
# Pre-condition:
#   - proj_dir is a string representing a directory path
#   - os.path.join(proj_dir, "phases.json") resolves to a regular file whose content is valid JSON
#
# Post-condition:
#   - Returns the Python object obtained by parsing the JSON content of os.path.join(proj_dir, "phases.json")
#   - The returned object is a dict that contains the key "phases" mapping to a list
#   - Each element of the "phases" list is a dict with integer "phase" and string "name" keys
# [SPEC]

# [INFO]
# (no callees)
# [INFO]

def _load_phases(proj_dir):
    """Load phases.json from the project root."""
    phases_path = os.path.join(proj_dir, "phases.json")
    with open(phases_path, "r") as f:
        return json.load(f)

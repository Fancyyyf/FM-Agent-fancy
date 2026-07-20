"""Probe script: verify _load_phases returns unvalidated JSON when phases.json contains an empty object {}.

Spec claim: _load_phases returns a dict with "phases" key mapping to a list of dicts
             with integer "phase" and string "name" keys.
Bug: The function returns whatever JSON is in the file without validating structure.
     An empty JSON object {} is accepted without error.
"""

import sys
import os
import tempfile
import json

# Ensure repo root is on sys.path so `src` module is importable
# Script is in fm_agent/bug_validation/ — go up 3 levels to repo root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

try:
    from src.generate_topdown_layers import _load_phases
except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)

try:
    # Create a temp directory with a phases.json containing an empty object
    with tempfile.TemporaryDirectory() as tmpdir:
        phases_path = os.path.join(tmpdir, "phases.json")
        with open(phases_path, "w") as f:
            f.write("{}")

        actual = _load_phases(tmpdir)

        # Spec requires: returned object is a dict with "phases" key
        # Bug: returns {} without "phases" key
        expected_has_phases_key = True
        actual_has_phases_key = "phases" in actual

        if not actual_has_phases_key:
            # Bug confirmed: empty JSON returned without validation
            print(f'CONFIRMED — returned object lacks "phases" key, actual: {actual!r}')
        else:
            print(f'NOT CONFIRMED — actual matched expected: {actual!r}')

except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)

import sys
import os
import json
import tempfile

try:
    from src.pipeline_setup import _filter_phases_to_submodules

    # Create a temporary phases.json with a phase that lacks a "phase" key.
    phases_content = {
        "phases": [
            {
                # Intentionally NO "phase" key here.
                "name": "missing_phase_key",
                "modules": [
                    {
                        "name": "test_module",
                        "source_files": ["outside_scope/file.py"]
                    }
                ]
            }
        ]
    }

    tmpdir = tempfile.mkdtemp()
    phases_path = os.path.join(tmpdir, "phases.json")
    with open(phases_path, "w") as f:
        json.dump(phases_content, f)

    # Call with a submodules list that does NOT match any source_file,
    # so files get removed and modified_modules is non-empty.
    result = _filter_phases_to_submodules(phases_path, ["core"])

    mods = result.get("modified_modules", [])
    if not mods:
        print("NOT CONFIRMED — no modules were modified; bug path not triggered")
        sys.exit(0)

    actual_phase = mods[0].get("phase")
    expected_phase_type = type(1)  # Should be int

    # Bug: phase.get("phase") returns None when the key is absent.
    if actual_phase is None:
        print(f"CONFIRMED — actual phase: {actual_phase!r} (None) | expected: an integer (int)")
    elif isinstance(actual_phase, int):
        print(f"NOT CONFIRMED — actual phase is int ({actual_phase!r}); no bug detected")
    else:
        print(f"NOT CONFIRMED — actual phase is {actual_phase!r} (type: {type(actual_phase).__name__}), not None")

    # Cleanup
    os.remove(phases_path)
    os.rmdir(tmpdir)

except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)

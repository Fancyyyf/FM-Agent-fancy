import json
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

try:
    from src.pipeline_setup import _deduplicate_phases

    with tempfile.TemporaryDirectory() as tmpdir:
        phases_path = os.path.join(tmpdir, "phases.json")

        # phases.json with string phase numbers: "10" and "2".
        # Numeric order: 2 < 10  → phase 2 should process first.
        # Lexicographic: "10" < "2" → phase "10" processes first (BUG).
        # Both phases share "shared.py" — the first-processed phase keeps it.
        phases_data = {
            "phases": [
                {
                    "phase": "10",
                    "modules": [
                        {"name": "mod_a", "source_files": ["shared.py", "a.py"]}
                    ],
                },
                {
                    "phase": "2",
                    "modules": [
                        {"name": "mod_b", "source_files": ["shared.py", "b.py"]}
                    ],
                },
            ]
        }
        with open(phases_path, "w") as f:
            json.dump(phases_data, f)

        result = _deduplicate_phases(tmpdir)
        modified = result.get("modified_modules", [])

        bug_confirmed = False
        issues = []

        # Check 1: If phase "2" (numeric 2) lost shared.py, that means phase "10"
        # was processed first (lexicographic sort of strings) — the BUG.
        for mod in modified:
            if str(mod["phase"]) == "2" and "shared.py" in mod.get(
                "removed_files", []
            ):
                bug_confirmed = True
                issues.append(
                    "Phase 2 (smaller numeric) lost shared.py to phase 10 (larger numeric) — "
                    "lexicographic sort of string phases produced wrong ordering"
                )
                break

        # Check 2: Returned phase values must be int per spec, but code preserves original type.
        for mod in modified:
            if not isinstance(mod["phase"], int):
                bug_confirmed = True
                issues.append(
                    f"Returned phase type is {type(mod['phase']).__name__} "
                    f"(value {mod['phase']!r}), spec requires int"
                )

        if bug_confirmed:
            print(f"CONFIRMED — {', '.join(issues)}")
        else:
            print(f"NOT CONFIRMED — phases sorted correctly despite string types")

except Exception as e:
    print(f"ERROR: {e}")
    import traceback

    traceback.print_exc()
    sys.exit(1)

"""Probe for bug: _collapse_phases_to_one inserts "Phase N (Name): " prefix
before each phase's description instead of just joining stripped non-empty
descriptions with blank lines.

Bug ID: src--pipeline_setup-py--_collapse_phases_to_one

Expected (spec): merged description = stripped non-empty descriptions of all
phases joined by "\n\n", no prefixes.

Actual (bug): code produces "Phase 1 (Name1): desc1\n\nPhase 2 (Name2): desc2"
"""

import json
import os
import shutil
import sys
import tempfile
from pathlib import Path


def main():
    # Ensure the repo root is importable
    _REPO_ROOT = Path(__file__).resolve().parent.parent.parent
    if str(_REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(_REPO_ROOT))

    # --- Save and sanitize environment ---
    _saved_env = {k: os.environ.get(k) for k in (
        "FM_AGENT_CONFIG", "LLM_API_KEY", "LLM_API_BASE_URL", "FM_AGENT_MODEL_BACKEND",
        "LLM_MODEL", "LLM_EFFORT", "OPENCODE_MODEL_PROVIDER", "LLM_API_STYLE",
        "MAX_SPC_ITER", "GRANULARITY", "MAX_WORKERS", "OPENCODE_MAX_RETRIES",
        "BUG_VALIDATION_MAX_RETRIES", "OPENCODE_TIMEOUT_SECONDS",
        "FM_AGENT_DOMAIN_KNOWLEDGE",
    )}
    for k in _saved_env:
        if k in os.environ:
            del os.environ[k]

    tmpdir = None
    try:
        # --- Step 1: Create a temporary work_dir with phases.json ---
        tmpdir = tempfile.mkdtemp(prefix="probe_collapse_phases_")
        phases_path = os.path.join(tmpdir, "phases.json")

        phases_data = {
            "phases": [
                {
                    "phase": 1,
                    "name": "Analysis Phase",
                    "description": "First phase handles initial setup",
                    "modules": [
                        {"name": "mod_a", "source_files": ["a.py"]},
                    ],
                    "depends_on_phases": [],
                },
                {
                    "phase": 2,
                    "name": "Verification Phase",
                    "description": "Second phase verifies the results",
                    "modules": [
                        {"name": "mod_b", "source_files": ["b.py"]},
                    ],
                    "depends_on_phases": [1],
                },
                {
                    "phase": 3,
                    "name": "Cleanup Phase",
                    "description": "  Final phase does cleanup  ",
                    "modules": [
                        {"name": "mod_c", "source_files": ["c.py"]},
                    ],
                    "depends_on_phases": [2],
                },
            ]
        }
        with open(phases_path, "w") as f:
            json.dump(phases_data, f, indent=2)

        # --- Step 2: Setup domain context files ---
        domain_dir = os.path.join(tmpdir, "spec_prompts", "domain_context")
        os.makedirs(domain_dir, exist_ok=True)
        with open(os.path.join(domain_dir, "phase_01_types.txt"), "w") as f:
            f.write("TypeSetA from phase 1")
        with open(os.path.join(domain_dir, "phase_02_types.txt"), "w") as f:
            f.write("TypeSetB from phase 2")
        with open(os.path.join(domain_dir, "phase_03_types.txt"), "w") as f:
            f.write("TypeSetC from phase 3")
        # Also create a non-phase file that should survive
        with open(os.path.join(domain_dir, "engine_overview.txt"), "w") as f:
            f.write("Engine overview")

        # --- Step 3: Import and call the function under test ---
        from src.pipeline_setup import _collapse_phases_to_one
        _collapse_phases_to_one(tmpdir)

        # --- Step 4: Read back and verify ---
        with open(phases_path, "r") as f:
            result = json.load(f)

        merged_phases = result.get("phases", [])
        assert len(merged_phases) == 1, (
            f"Expected 1 merged phase, got {len(merged_phases)}"
        )
        actual_description = merged_phases[0].get("description", "")

        # Spec-correct expected: just stripped non-empty descriptions joined by "\n\n"
        expected_description = (
            "First phase handles initial setup\n\n"
            "Second phase verifies the results\n\n"
            "Final phase does cleanup"
        )

        # The bug: code prepends "Phase N (Name): " prefix
        # So actual will contain "Phase 1 (Analysis Phase): First phase..."
        # This does NOT match expected (just the raw descriptions)
        passed = actual_description != expected_description

        # --- Step 5: Verify domain context merge ---
        merged_types_path = os.path.join(domain_dir, "phase_01_types.txt")
        with open(merged_types_path, "r") as f:
            actual_types_content = f.read()

        # Check that only phase_01_types.txt remains
        remaining_types_files = [
            f for f in os.listdir(domain_dir)
            if f.startswith("phase_") and f.endswith("_types.txt")
        ]
        engine_overview_still_exists = os.path.exists(
            os.path.join(domain_dir, "engine_overview.txt")
        )

        if passed:
            print(
                f"CONFIRMED — description has unwanted phase prefix: "
                f"actual: {actual_description!r} | "
                f"expected: {expected_description!r}"
            )
        else:
            print(
                f"NOT CONFIRMED — description matches spec: {actual_description!r}"
            )

    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"ERROR: {type(e).__name__}: {e}")

    finally:
        # Restore environment
        for k, v in _saved_env.items():
            if v is not None:
                os.environ[k] = v
            elif k in os.environ:
                del os.environ[k]

        # Clean up temp directory
        if tmpdir:
            shutil.rmtree(tmpdir, ignore_errors=True)


if __name__ == "__main__":
    main()

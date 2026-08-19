"""
Probe script for bug: _remove_stale_extracted does not clean up extracted
directories for source files not tracked in phases.json and not present in
modified_functions, leaving orphaned extracted function files.

Bug ID: src--incremental_reasoner-py--_remove_stale_extracted

Scenario:
  - Source file old/untracked.py once existed and had extracted functions.
  - It was removed from phases.json (pipeline config) and the file itself
    was deleted — so it is in neither modified_functions nor phases.json.
  - _remove_stale_extracted should remove its stale extracted directory,
    but the current code never visits it, so orphans remain.
"""

import json
import os
import shutil
import sys
import tempfile

# Ensure the repo root is on sys.path so `from src.incremental_reasoner`
# resolves.  The probe runs from the repo root, but the script's directory
# (fm_agent/bug_validation/) would otherwise shadow the root import.
_script_dir = os.path.dirname(os.path.abspath(__file__))
_repo_root = os.path.dirname(os.path.dirname(_script_dir))
sys.path.insert(0, _repo_root)

try:
    from src.incremental_reasoner import _remove_stale_extracted
except ImportError as e:
    print(f"ERROR: cannot import _remove_stale_extracted: {e}")
    sys.exit(1)


def main():
    """Set up a minimal project tree, run _remove_stale_extracted, assert result."""

    # ── 1. Build a temporary project directory ────────────────────────────
    proj_dir = tempfile.mkdtemp(prefix="fm_agent_probe_")
    try:
        # phases.json tracked source file — NOT the orphan
        tracked_rel = "src/tracked.py"
        tracked_abs = os.path.abspath(os.path.join(proj_dir, tracked_rel))

        # The orphan source file that was removed from the pipeline:
        #   - was previously in phases.json → extracted functions exist
        #   - is now deleted from disk
        #   - removed from phases.json
        #   - not in modified_functions (wasn't modified; was just un-tracked)
        orphan_rel = "old/untracked.py"
        orphan_abs = os.path.abspath(os.path.join(proj_dir, orphan_rel))

        # Compute the extracted-function directory for the orphan file
        extracted_base = os.path.join(proj_dir, "fm_agent", "extracted_functions")
        orphan_dir_name = orphan_rel.rsplit(".", 1)[0].replace("/", "-").replace(".", "-")
        orphan_func_dir = os.path.join(extracted_base, "old", "untracked-py")
        # Actually, let's use _src_rel_to_func_dir if accessible, or hardcode:
        # old/untracked.py → extracted_functions/old/untracked-py/

        # ── 2. Create the tracked source file (so phases.json is valid) ──
        os.makedirs(os.path.join(proj_dir, "src"), exist_ok=True)
        with open(tracked_abs, "w") as f:
            f.write("def tracked_func():\n    return 1\n")

        # ── 3. Create phases.json that ONLY lists the tracked file ────────
        os.makedirs(os.path.join(proj_dir, "fm_agent"), exist_ok=True)
        phases = {
            "phases": [
                {
                    "name": "test-phase",
                    "modules": [
                        {
                            "name": "test_module",
                            "source_files": [tracked_rel],
                        }
                    ],
                }
            ]
        }
        with open(os.path.join(proj_dir, "fm_agent", "phases.json"), "w") as f:
            json.dump(phases, f)

        # ── 4. Create stale extracted-function files for the orphan ───────
        os.makedirs(orphan_func_dir, exist_ok=True)

        orphan_func_file = os.path.join(orphan_func_dir, "old_func.py")
        orphan_spec_file = orphan_func_file + ".spec.json"
        orphan_info_file = orphan_func_file + ".info.json"

        with open(orphan_func_file, "w") as f:
            f.write("def old_func():\n    pass\n")
        with open(orphan_spec_file, "w") as f:
            json.dump({"pre": "true", "post": "true"}, f)
        with open(orphan_info_file, "w") as f:
            json.dump({"fqn": "old_func", "file": "old/untracked.py"}, f)

        # Sanity: files exist before the call
        assert os.path.isfile(orphan_func_file), "orphan func file missing"
        assert os.path.isfile(orphan_spec_file), "orphan spec file missing"
        assert os.path.isfile(orphan_info_file), "orphan info file missing"

        # ── 5. Call _remove_stale_extracted ───────────────────────────────
        #  modified_functions is empty — the orphan source is not there
        _remove_stale_extracted(proj_dir, {})

        # ── 6. Assert ─────────────────────────────────────────────────────
        # Specification claim: every remaining file under extracted_functions/
        # corresponds to a source function that exists in a tracked source
        # file. The orphan file path is neither in phases.json nor in
        # modified_functions, so it is untracked. Its extracted files should
        # be removed.
        stale_remain = os.path.isfile(orphan_func_file)
        spec_remain = os.path.isfile(orphan_spec_file)
        info_remain = os.path.isfile(orphan_info_file)

        expected_removed = not stale_remain and not spec_remain and not info_remain
        actual_stale = stale_remain or spec_remain or info_remain

        if actual_stale:
            print(
                "CONFIRMED"
                f" — orphan extracted files remain after _remove_stale_extracted"
                f" (func_file={stale_remain}, spec={spec_remain}, info={info_remain})"
                f" | expected: all removed (orphans cleaned)"
            )
        else:
            print(
                "NOT CONFIRMED"
                f" — all orphan extracted files were removed as expected"
                f" (func_file={stale_remain}, spec={spec_remain}, info={info_remain})"
            )

    except Exception as exc:
        print(f"ERROR: {exc}")
        sys.exit(1)
    finally:
        # Clean up temp dir
        shutil.rmtree(proj_dir, ignore_errors=True)


if __name__ == "__main__":
    main()

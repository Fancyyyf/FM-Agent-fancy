"""Probe: verify _sync_domain_context retries on subprocess failure.

Bug claim: _sync_domain_context does not implement retry logic and raises
subprocess.CalledProcessError on first failure, violating the best-effort spec.

Actual spec requirement: Retry up to OPENCODE_MAX_RETRIES with delay; after
exhaustion, log a warning and return without raising.
"""

import sys
import os
import json
import tempfile
import subprocess
import unittest.mock

# ── setup: import the package via its public entry point ──────────────────
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    import src.pipeline_setup as pkg
except Exception as e:
    print(f'ERROR: could not import src.pipeline_setup: {e}')
    sys.exit(1)

CONFIRMED_MSG = "CONFIRMED"
NOT_CONFIRMED_MSG = "NOT CONFIRMED"


def _create_minimal_phases(work_dir, phase_num, source_files):
    """Create a minimal phases.json with one phase owning some source files."""
    phases_path = os.path.join(work_dir, "phases.json")
    data = {
        "phases": [
            {
                "phase": phase_num,
                "modules": [{"source_files": list(source_files)}],
            }
        ]
    }
    with open(phases_path, "w") as f:
        json.dump(data, f)


def main():
    proj_dir = tempfile.mkdtemp(prefix="fm_probe_proj_")
    work_dir = tempfile.mkdtemp(prefix="fm_probe_work_")

    try:
        # Create domain_context directory (required to pass early-return guard)
        domain_dir = os.path.join(work_dir, "spec_prompts", "domain_context")
        os.makedirs(domain_dir, exist_ok=True)

        # Create a minimal phases.json so _phase_source_files finds phase 1
        _create_minimal_phases(work_dir, 1, ["src/example.py"])

        # Patch run_opencode_traced to always fail with CalledProcessError
        call_count = [0]

        def failing_traced(**kwargs):
            call_count[0] += 1
            raise subprocess.CalledProcessError(returncode=1, cmd="mock-cmd")

        # Patch time.sleep to avoid waiting 10s per retry
        with unittest.mock.patch.object(pkg, "run_opencode_traced", failing_traced), \
             unittest.mock.patch("time.sleep", return_value=None):

            # Call the function — spec says it should retry and return without raising
            try:
                pkg._sync_domain_context(
                    proj_dir=proj_dir,
                    work_dir=work_dir,
                    changed_phases={1},
                    phase_cleanup=None,
                )
            except subprocess.CalledProcessError:
                # Bug CONFIRMED: function raised instead of retrying
                expected_retries = pkg.OPENCODE_MAX_RETRIES
                print(
                    f"{CONFIRMED_MSG} — _sync_domain_context raised CalledProcessError "
                    f"after {call_count[0]} call(s); expected {expected_retries} retries "
                    f"per spec (OPENCODE_MAX_RETRIES={expected_retries})"
                )
                return

        # Check that retries happened
        expected_retries = pkg.OPENCODE_MAX_RETRIES
        if call_count[0] == expected_retries:
            print(
                f"{NOT_CONFIRMED_MSG} — _sync_domain_context retried {call_count[0]} "
                f"times and returned without raising, matching the spec "
                f"(OPENCODE_MAX_RETRIES={expected_retries})"
            )
        elif call_count[0] > 0:
            print(
                f"{NOT_CONFIRMED_MSG} — _sync_domain_context retried {call_count[0]} "
                f"times before returning; spec requires up to {expected_retries} retries "
                f"(OPENCODE_MAX_RETRIES={expected_retries}). Retry logic exists, "
                f"just with a different count than expected."
            )
        else:
            print(
                f"{CONFIRMED_MSG} — _sync_domain_context called run_opencode_traced "
                f"0 times (unexpected)"
            )

    finally:
        import shutil
        shutil.rmtree(proj_dir, ignore_errors=True)
        shutil.rmtree(work_dir, ignore_errors=True)


if __name__ == "__main__":
    main()

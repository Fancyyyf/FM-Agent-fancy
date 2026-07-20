"""Probe for _validate bug: spec says it produces/overwrites a result JSON, but code reads it instead."""
import sys
import os
import tempfile
import shutil
from unittest.mock import patch

# Ensure the project root is on the Python path for import
_script_dir = os.path.dirname(os.path.abspath(__file__))
_proj_root = os.path.dirname(os.path.dirname(_script_dir))
if _proj_root not in sys.path:
    sys.path.insert(0, _proj_root)

# Package entry point: use the src.verification module
try:
    from src.verification import _validate_single_bug
except ImportError as e:
    print(f"ERROR: Could not import _validate_single_bug: {e}")
    print("NOT CONFIRMED — import failed")
    sys.exit(1)

# Set up a temporary directory structure that simulates the expected layout.
# _validate (the function under test) computes:
#   result_json_rel = os.path.join(
#       os.path.relpath(output_dir, proj_dir),
#       os.path.splitext(rel)[0] + ".json",
#   )
# and then calls _validate_single_bug(result_json_rel, proj_dir, work_dir).
# The spec says _validate produces/overwrites the JSON at result_json_rel.
# The code does NOT write to result_json_rel — it passes it to _validate_single_bug
# which only READS it (via an opencode process).
#
# If the JSON doesn't already exist at that path, the code fails instead of producing it.

tmpdir = tempfile.mkdtemp(prefix="fm_agent_probe_")
try:
    proj_dir = os.path.join(tmpdir, "project")
    work_dir = os.path.join(proj_dir, "fm_agent")
    output_dir = os.path.join(work_dir, "logic_verification_results")

    os.makedirs(output_dir, exist_ok=True)

    # Simulate _validate's logic: given a rel like "src/incremental_reasoner-py/write.py"
    # it computes a result_json_rel pointing to
    # "fm_agent/logic_verification_results/src/incremental_reasoner-py/write.json"
    rel = "src/incremental_reasoner-py/write.py"
    result_json_rel = os.path.join(
        os.path.relpath(output_dir, proj_dir),
        os.path.splitext(rel)[0] + ".json",
    )

    # Expected path to the result JSON (resolved relative to proj_dir)
    expected_result_path = os.path.normpath(os.path.join(proj_dir, result_json_rel))
    expected_result_dir = os.path.dirname(expected_result_path)

    # Ensure the parent dir exists but NOT the JSON file itself — the spec says
    # _validate should produce/overwrite it, so it should handle this case.
    os.makedirs(expected_result_dir, exist_ok=True)

    # Verify the JSON does NOT exist before calling the function
    if os.path.exists(expected_result_path):
        os.remove(expected_result_path)

    # Call _validate_single_bug with run_opencode_traced mocked to avoid the
    # heavy opencode subprocess call. This lets us test whether the code produces
    # the result JSON at the expected path WITHOUT running opencode.
    error_occurred = False
    error_msg = ""
    try:
        with patch("src.verification.run_opencode_traced") as mock_traced, \
             patch("src.verification.build_llm_cli_command") as mock_build, \
             patch("src.verification.list_staged_domain_knowledge_relpaths", return_value=[]), \
             patch("src.verification.format_domain_knowledge_bullets", return_value=""):
            mock_build.return_value = ["echo", "mocked"]
            mock_traced.return_value = None
            _validate_single_bug(result_json_rel, proj_dir, work_dir)
    except Exception as exc:
        error_occurred = True
        error_msg = str(exc)

    # Check whether the result JSON was produced at the expected path.
    # Per the spec, it should exist. Per the actual code, it won't.
    json_produced = os.path.exists(expected_result_path)

    # The bug is confirmed if the result JSON was NOT produced.
    # Spec says _validate produces/overwrites the JSON.
    # Actual code does NOT write to result_json_rel — it only reads from it.
    bug_confirmed = not json_produced

    if bug_confirmed:
        reasons = []
        if not json_produced:
            reasons.append(
                f"no result JSON was produced at {result_json_rel} "
                f"(spec says it should be produced/overwritten)"
            )
        if error_occurred:
            reasons.append(f"function raised: {error_msg[:150]}")
        print(f"CONFIRMED — {'. '.join(reasons)}")
    else:
        print("NOT CONFIRMED — the function produced or overwrote the result JSON as the spec requires")

finally:
    shutil.rmtree(tmpdir, ignore_errors=True)

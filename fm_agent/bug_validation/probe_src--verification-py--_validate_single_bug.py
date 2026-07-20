import json
import os
import shutil
import sys
import tempfile

# Ensure the repo root is on sys.path so `import src.verification` works
repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, repo_root)

try:
    from src.verification import _validate_single_bug

    proj_dir = tempfile.mkdtemp(prefix="bug_probe_")

    # Set up the directory structure needed for the early-return path
    bug_validation_dir = os.path.join(proj_dir, "fm_agent", "bug_validation")
    os.makedirs(bug_validation_dir, exist_ok=True)

    # Create a valid result.json to trigger the early return
    result_json = {"id": "src--verification-py--_validate_single_bug", "confirmation_status": "confirmed", "attempts": 1}
    result_json_rel = "fm_agent/logic_verification_results/src/verification-py/_validate_single_bug.json"
    # bug_id derived from result_json_rel: src--verification-py--_validate_single_bug
    bug_id = "src--verification-py--_validate_single_bug"
    result_path = os.path.join(proj_dir, "fm_agent", "bug_validation", f"{bug_id}.result.json")
    with open(result_path, "w") as f:
        json.dump(result_json, f)

    # The prompt file that _validate_single_bug will create
    prompt_path = os.path.join(proj_dir, "fm_agent", "bug_validation", f"bug_validator_{bug_id}.md")

    # Call with resume=True — should return early from line 400
    _validate_single_bug(result_json_rel=result_json_rel, proj_dir=proj_dir, resume=True)

    # SPEC: prompt file must be removed on exit regardless of success/failure
    # BUG: early return at line 400 skips the finally cleanup at lines 454-458
    if os.path.exists(prompt_path):
        print(f"CONFIRMED — prompt file not cleaned up: {prompt_path}")
    else:
        print(f"NOT CONFIRMED — prompt file was cleaned up (spec-compliant)")

    # Cleanup
    shutil.rmtree(proj_dir, ignore_errors=True)

except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)

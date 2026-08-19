"""Probe script for _validate_single_bug bug validation.

Tests whether _validate_single_bug dispatches the bug-validation agent
(via run_opencode_traced) when resume=False and no result marker exists.

Spec claim: the function dispatches a bug-validation agent.
Code reality: the function calls run_opencode_traced at line 434 of src/verification.py
(lines 84-106 in extracted form).

If dispatch is called -> NOT CONFIRMED (code matches spec -> false positive).  
If dispatch is NOT called -> CONFIRMED (code violates spec).
"""

import sys
import os

# Ensure repo root is on sys.path so 'src' can be imported
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

import tempfile
import json
from unittest.mock import patch, MagicMock

# ── Mock setup ──────────────────────────────────────────────────────────

probe_tmp = tempfile.TemporaryDirectory(prefix="bug_validator_probe_")
tmp_dir = probe_tmp.name
os.makedirs(os.path.join(tmp_dir, "fm_agent", "bug_validation"), exist_ok=True)

dispatch_called = []
dispatch_kwargs = []


def fake_run_opencode_traced(proj_dir, work_dir, command, stage, function_ids,
                             input_files, output_files, summary, metadata):
    dispatch_called.append(True)
    dispatch_kwargs.append({
        "proj_dir": proj_dir,
        "work_dir": work_dir,
        "stage": stage,
        "output_files": output_files,
        "summary": summary,
        "metadata": metadata,
    })
    # Simulate agent producing the result.json marker so function returns normally
    bug_id = metadata.get("bug_id", "unknown")
    result_path = os.path.join(proj_dir, "fm_agent", "bug_validation", f"{bug_id}.result.json")
    os.makedirs(os.path.dirname(result_path), exist_ok=True)
    with open(result_path, "w") as f:
        json.dump({"confirmation_status": "confirmed"}, f)


BUG_VALIDATOR_MD_PATH = os.path.join(REPO_ROOT, "md", "bug_validator.md")

actual = None
expected = "dispatch called"
passed = False
error_msg = None

try:
    with patch("src.opencode_trace.run_opencode_traced", side_effect=fake_run_opencode_traced), \
         patch("src.verification.run_opencode_traced", side_effect=fake_run_opencode_traced), \
         patch("src.llm_client.build_llm_cli_command", return_value=["opencode", "run"]), \
         patch("src.verification.build_llm_cli_command", return_value=["opencode", "run"]), \
         patch("src.opencode_trace.function_id_from_result_path", return_value="test_func_123"), \
         patch("src.verification.function_id_from_result_path", return_value="test_func_123"), \
         patch("src.domain_knowledge.list_staged_domain_knowledge_relpaths", return_value=[]), \
         patch("src.verification.list_staged_domain_knowledge_relpaths", return_value=[]), \
         patch("src.verification.format_domain_knowledge_bullets", return_value=""), \
         patch("src.verification.config") as mock_config, \
         patch("src.verification.OPENCODE_BUG_VALIDATION_MODEL", "fake-model"), \
         patch("src.verification.logging") as mock_logging:

        mock_config.BUG_VALIDATION_MAX_RETRIES = 3

        # Import after patching
        from src.verification import _validate_single_bug

        # Test: resume=False, no existing result -> dispatch should be called
        dispatch_called.clear()
        dispatch_kwargs.clear()
        result_json_rel = "fm_agent/logic_verification_results/src/verification-py/_validate_single_bug.json"

        _validate_single_bug(
            result_json_rel=result_json_rel,
            proj_dir=tmp_dir,
            work_dir=tmp_dir,
            resume=False,
            bug_validator_path=BUG_VALIDATOR_MD_PATH,
        )

        if dispatch_called:
            actual = "dispatch called"
        else:
            actual = "dispatch NOT called"

        passed = actual != expected  # True only if dispatch missing (bug real)

except Exception as e:
    error_msg = str(e)
    import traceback
    traceback.print_exc()

# ── Output verdict ───────────────────────────────────────────────────────

if error_msg:
    print(f"ERROR: {error_msg}")
    sys.exit(1)
elif passed:
    print(f"CONFIRMED — actual: {actual!r} | expected: {expected!r}")
else:
    detail = ""
    if dispatch_kwargs:
        dk = dispatch_kwargs[0]
        detail = (
            f" | output_files={dk['output_files']} | "
            f"stage={dk['stage']} | summary={dk['summary']}"
        )
    print(f"NOT CONFIRMED — actual: {actual!r} | expected: {expected!r}{detail}")

probe_tmp.cleanup()

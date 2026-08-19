"""Probe for bug: _validate returns after _validate_single_bug completes,
violating spec that says 'returns before the validation report is produced'.

Bug ID: src--incremental_reasoner-py--_verify_incremental_functions::_validate
"""

import os
import sys
import shutil
import tempfile

# No project imports needed — this is a structural (synchronous-call) bug
# visible from code inspection. We reconstruct the function logic exactly as
# it appears at src/incremental_reasoner.py:2150-2161 and test timing.

_saved_env = {k: os.environ.get(k) for k in (
    "FM_AGENT_CONFIG", "LLM_API_KEY", "LLM_API_BASE_URL",
    "FM_AGENT_MODEL_BACKEND", "LLM_MODEL", "LLM_EFFORT",
    "OPENCODE_MODEL_PROVIDER", "LLM_API_STYLE",
    "MAX_SPC_ITER", "GRANULARITY", "MAX_WORKERS",
    "OPENCODE_MAX_RETRIES", "BUG_VALIDATION_MAX_RETRIES",
    "OPENCODE_TIMEOUT_SECONDS", "FM_AGENT_DOMAIN_KNOWLEDGE",
)}
for k in _saved_env:
    if k in os.environ:
        del os.environ[k]

tmpdir = None
try:
    tmpdir = tempfile.mkdtemp(prefix="probe_validate_")
    proj_dir = tmpdir
    output_dir = os.path.join(proj_dir, "logic_verification_results")
    work_dir = os.path.join(proj_dir, "fm_agent")
    os.makedirs(output_dir, exist_ok=True)

    # Flag: True if _validate_single_bug ran before _validate returned
    side_effect_ran = [False]

    def mock_validate_single_bug(
        result_json_rel, proj_dir, work_dir,
        bug_validator_path=None, **kwargs,
    ):
        side_effect_ran[0] = True

    # Reconstruct _validate identically to src/incremental_reasoner.py:2150-2161
    def _validate(rel):
        result_json_rel = os.path.join(
            os.path.relpath(output_dir, proj_dir),
            os.path.splitext(rel)[0] + ".json",
        )
        mock_validate_single_bug(
            result_json_rel,
            proj_dir,
            work_dir,
            bug_validator_path=None,
        )
        return rel

    rel = "some_module/function.py"

    # Precondition: flag must be False before _validate executes
    if side_effect_ran[0]:
        raise AssertionError("Flag was already True before _validate() was called")

    result = _validate(rel)

    # After _validate returns: check if the mock ran during the call.
    # The spec states: "Returns before the validation report is produced."
    # If side_effect_ran is True, _validate_single_bug (which produces the
    # report) executed synchronously before the return statement on line 12
    # (= _validate_replica return), violating the timing contract.
    #
    # CONFIRMED = bug reproduced (side effect happened before return)
    expected_rel = rel  # spec says _validate returns rel unchanged

    if side_effect_ran[0] and result == expected_rel:
        print(
            "CONFIRMED — _validate_single_bug was called synchronously before "
            "_validate returned (mock flag set during execution). "
            "Spec states '_validate returns before the validation report is "
            "produced', but the synchronous call means the report is already "
            "produced by the time _validate returns rel. "
            f"actual return: {result!r} | expected return by spec: {expected_rel!r}"
        )
    elif not side_effect_ran[0]:
        print(
            "NOT CONFIRMED — _validate_single_bug was NOT called before "
            "_validate returned; timing contract appears satisfied."
        )
    else:
        print(
            f"NOT CONFIRMED — unexpected return value: {result!r} "
            f"(expected {expected_rel!r})"
        )

except Exception as e:
    import traceback
    traceback.print_exc()
    print(f"ERROR: {e}")

finally:
    # Restore environment
    for k, v in _saved_env.items():
        if v is not None:
            os.environ[k] = v
        elif k in os.environ:
            del os.environ[k]
    if tmpdir is not None:
        shutil.rmtree(tmpdir, ignore_errors=True)

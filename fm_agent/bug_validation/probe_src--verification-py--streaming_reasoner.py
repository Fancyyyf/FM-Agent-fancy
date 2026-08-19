#!/usr/bin/env python3
"""Probe for bug `src--verification-py--streaming_reasoner`.

Spec claim (relevant excerpt):
  "Only MISMATCH verdicts trigger bug validation; when proj_dir is provided,
   every MISMATCH is submitted to bug validation before return."
  and the summary must be generated "after the watch loop ends by any path,
   including user interruption".

Reported bug:
  In the KeyboardInterrupt handler of streaming_reasoner()
  (src/verification.py, ~lines 246-259), the code waits for the in-flight
  futures via future.result() but discards the returned verdict. A reasoning
  future that resolves with a MISMATCH verdict during interrupt handling is
  therefore never submitted to _validate_single_bug(), violating the absolute
  "every MISMATCH is submitted" requirement.

Strategy (deterministic, no FM-Agent workflow started):
  1. Fresh temp-dir fixture with one ready source file declared via file_list.
  2. Patch module-level collaborators of streaming_reasoner():
       - is_file_ready                -> always True
       - _verify_single_file          -> sleeps briefly (stays in flight),
                                         then returns (path, "MISMATCH")
       - _validate_single_bug         -> records the call, does nothing
       - _generate_validation_summary -> records the call, does nothing
       - time (module attribute)      -> shim whose sleep() raises
                                         KeyboardInterrupt on the loop's first
                                         poll, while the reasoning future is
                                         still in flight
  3. Call streaming_reasoner() with proj_dir provided.
  4. Oracle: the reasoning future resolved with MISMATCH, but
     _validate_single_bug was never called -> the interrupt path dropped a
     MISMATCH without submitting bug validation -> CONFIRMED.

FM-Agent self-validation guard compliance: this probe never starts an
FM-Agent workflow (no run_pipeline(), run_incremental_pipeline(), main.py,
FM-Agent CLI, OpenCode, or any FM-Agent subprocess). It unit-tests only
src.verification.streaming_reasoner with mocks, and every fixture/runtime
file lives under a fresh temporary directory owned by the probe.
"""

import os
import shutil
import sys
import tempfile
import time as real_time

# Resolve the repo root (probe lives in fm_agent/bug_validation/) so the
# package import works regardless of the caller's cwd.
_REPO_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
)
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

# Load the package via its package namespace (public entry point).
import src.verification as V  # noqa: E402


def main():
    tmp = tempfile.mkdtemp(prefix="probe_streaming_reasoner_")
    input_dir = os.path.join(tmp, "extracted_functions")
    output_dir = os.path.join(tmp, "logic_verification_results")
    proj_dir = tmp  # proj_dir is provided => every MISMATCH must be submitted
    work_dir = tmp
    os.makedirs(input_dir, exist_ok=True)
    os.makedirs(output_dir, exist_ok=True)

    victim_rel = "victim.py"
    victim_path = os.path.join(input_dir, victim_rel)
    with open(victim_path, "w", encoding="utf-8") as fh:
        fh.write("def victim():\n    return 42\n")

    calls = {"verify": [], "validate": [], "summary": []}
    verdict_holder = {}

    def fake_verify(file_path, in_dir, out_dir, language, work_dir=None, resume=False):
        # Simulate a verification that is still in flight when the interrupt
        # arrives, then resolves with a MISMATCH verdict.
        real_time.sleep(0.4)
        verdict_holder["verdict"] = "MISMATCH"
        calls["verify"].append(file_path)
        return file_path, "MISMATCH"

    def fake_validate(result_json_rel, proj_dir_arg, work_dir_arg=None,
                      resume=False, bug_validator_path=None):
        calls["validate"].append(result_json_rel)
        return result_json_rel

    def fake_summary(dir_arg):
        calls["summary"].append(dir_arg)

    class FakeTime:
        """Raises KeyboardInterrupt on the watch loop's first poll."""

        def __init__(self):
            self.sleep_calls = 0

        def sleep(self, seconds):
            self.sleep_calls += 1
            raise KeyboardInterrupt()

        def __getattr__(self, name):
            return getattr(real_time, name)

    originals = {
        "is_file_ready": V.is_file_ready,
        "_verify_single_file": V._verify_single_file,
        "_validate_single_bug": V._validate_single_bug,
        "_generate_validation_summary": V._generate_validation_summary,
        "time": V.time,
    }

    crashed = None
    try:
        V.is_file_ready = lambda path: True
        V._verify_single_file = fake_verify
        V._validate_single_bug = fake_validate
        V._generate_validation_summary = fake_summary
        V.time = FakeTime()

        V.streaming_reasoner(
            input_dir=input_dir,
            output_dir=output_dir,
            file_list=[victim_rel],
            proj_dir=proj_dir,
            work_dir=work_dir,
            poll_interval=0.05,
            spec_procs=None,
            already_processed=None,
            resume=False,
            bug_validator_path=None,
        )
    except KeyboardInterrupt:
        crashed = "KeyboardInterrupt escaped streaming_reasoner (unexpected)"
    except Exception as exc:  # noqa: BLE001
        crashed = f"{type(exc).__name__}: {exc}"
    finally:
        for name, value in originals.items():
            setattr(V, name, value)

    if crashed is not None:
        print(f"ERROR: {crashed}")
        sys.exit(1)

    verdict = verdict_holder.get("verdict")
    n_verify = len(calls["verify"])
    n_validate = len(calls["validate"])

    detail = (
        f"verdict={verdict!r} | verify_calls={n_verify} | "
        f"bug_validation_submissions={n_validate} | proj_dir=provided | "
        f"expected_submissions>=1"
    )

    if verdict == "MISMATCH" and n_verify == 1 and n_validate == 0:
        # The reasoning future resolved with MISMATCH during interrupt
        # handling, yet no bug validation was ever submitted.
        print(
            "CONFIRMED - MISMATCH resolved during interrupt handling was never "
            f"submitted to bug validation ({detail}); spec requires every "
            "MISMATCH to be submitted to bug validation before return when "
            "proj_dir is provided"
        )
    elif n_validate >= 1:
        print(
            "NOT CONFIRMED - every MISMATCH was submitted to bug validation "
            f"as the spec requires ({detail})"
        )
    else:
        print(
            "NOT CONFIRMED - scenario did not produce the expected "
            f"in-flight MISMATCH state ({detail})"
        )

    shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: {type(exc).__name__}: {exc}")
        sys.exit(1)

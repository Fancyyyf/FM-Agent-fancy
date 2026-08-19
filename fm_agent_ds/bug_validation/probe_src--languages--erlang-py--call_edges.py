"""Probe for bug src--languages--erlang-py--call_edges.

Bug: _analysis_or_empty() catches ALL exceptions (line 607 of erlang.py),
silently returning ErlangAnalysis(edges={}). This causes call_edges() to return
{} for any internal error, violating the spec which restricts {} to only two
cases: (1) ELP backend unavailable, (2) no call edges extracted.

This test mocks _analyze_project to simulate a mid-analysis internal error
in a project where the backend IS available (Erlang files exist). The spec
requires a proper call-edges dict in this scenario, but the code returns {}.
"""

import os
import sys
import tempfile
from unittest.mock import patch


def main() -> int:
    tmpdir = tempfile.mkdtemp(prefix="probe_erlang_")
    try:
        # Create a directory with a minimal .erl file so the "no files" early
        # return in _analyze_project_uncached is bypassed.  This represents a
        # valid Erlang project whose backend is available.
        erl_path = os.path.join(tmpdir, "test.erl")
        with open(erl_path, "w", encoding="utf-8") as fh:
            fh.write("-module(test).\n-export([foo/0]).\nfoo() -> ok.\n")

        from src.languages.erlang import call_edges

        # --- Confirm expected spec behavior for a normal empty-project case ---
        result_normal = call_edges(tmpdir)
        # Without ELP installed, backend is unavailable → {} is spec-correct.

        # --- BUG TEST: internal error with available backend ---
        #
        # Monkey-patch _analyze_project to raise a RuntimeError.  This
        # simulates a scenario where:
        #   - ELP existed and started successfully (was "available")
        #   - An internal error occurred during analysis (JSON parse failure,
        #     broken pipe, OOM, etc.)
        #
        # The spec allows {} ONLY for "backend unavailable" or "no call edges
        # can be extracted".  A RuntimeError mid-analysis fits neither case,
        # so the spec-correct behaviour is to NOT return {}.  But the code's
        # catch-all in _analysis_or_empty swallows the exception and returns
        # ErlangAnalysis(edges={}), which call_edges() surfaces as {}.
        with patch(
            "src.languages.erlang._analyze_project",
            side_effect=RuntimeError("Simulated mid-analysis ELP internal error"),
        ):
            result_bug = call_edges(tmpdir)

        # Check: result_bug is {} because the catch-all swallowed RuntimeError.
        # The spec would require a call-edges dict (not {}) in this scenario.
        # Since the code returns {}, this CONFIRMS the bug.
        bug_present = isinstance(result_bug, dict) and result_bug == {}

        if bug_present:
            print(
                "CONFIRMED — call_edges() silently returned {{}} when an internal "
                "error (RuntimeError) was raised during analysis.  "
                "The spec allows {{}} only for backend-unavailable or "
                "no-call-edges cases, but _analysis_or_empty swallows ALL "
                "exceptions.  result_normal={!r}  result_bug={!r}".format(
                    result_normal, result_bug
                )
            )
        else:
            print(
                "NOT CONFIRMED — call_edges() returned {!r} instead of the "
                "expected empty dict".format(result_bug)
            )
        return 0

    except Exception as exc:
        print(f"ERROR: {exc}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        # Best-effort cleanup
        import shutil
        shutil.rmtree(tmpdir, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())

"""Probe script for bug: src--languages--erlang-py--function_spans

Bug: function_spans returns None when ELP is available and a file has been
indexed but contains no function definitions.  The spec requires an empty
list ([]) in that case.

Because ELP is not installed in this environment, we mock _analysis_or_empty
to return a controlled ErlangAnalysis whose spans dict simulates the exact
condition: ELP is available (non-empty analysis structure) but the target
file produced zero function symbols, so no entry was stored in the spans
mapping.  The .get() call then falls through to its None default — the bug.
"""
import sys
import os
import tempfile
import shutil
import unittest.mock as mock

# Ensure repo root is on sys.path so "from src..." resolves
_script_dir = os.path.dirname(os.path.abspath(__file__))
_repo_root = os.path.dirname(os.path.dirname(_script_dir))
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

try:
    from src.languages.erlang import function_spans, ErlangAnalysis

    # Create a minimal temp project with a zero-function .erl file.
    tmp_dir = tempfile.mkdtemp(prefix="erlang_test_")
    try:
        empty_erl = os.path.join(tmp_dir, "empty.erl")
        with open(empty_erl, "w") as f:
            f.write("% This Erlang module defines no functions\n")

        # Build a mock ErlangAnalysis that simulates "ELP available, file
        # indexed, but no function definitions found".  In the real
        # _analyze_project_uncached the spans dict only receives an entry
        # when file_functions is non-empty (line 576-578).  An empty file
        # therefore produces no spans entry.
        mock_analysis = ErlangAnalysis(
            functions={},    # empty — no functions found
            edges={},        # empty — no call graph
            # spans is intentionally left as its default (empty dict) to
            # match the real behaviour when a file has zero functions.
        )

        with mock.patch(
            "src.languages.erlang._analysis_or_empty",
            return_value=mock_analysis,
        ):
            actual = function_spans(tmp_dir, empty_erl)

        # SPEC says: "The returned list is empty when filepath contains no
        # function definitions and the backend is available."
        expected = []
        passed = actual != expected  # True → bug reproduced

        if passed:
            print(
                f"CONFIRMED — actual: {actual!r} | expected: {expected!r}"
            )
        else:
            print(
                f"NOT CONFIRMED — actual matched expected: {actual!r}"
            )
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)

except Exception as e:
    import traceback
    traceback.print_exc()
    print(f"ERROR: {e}")
    sys.exit(1)

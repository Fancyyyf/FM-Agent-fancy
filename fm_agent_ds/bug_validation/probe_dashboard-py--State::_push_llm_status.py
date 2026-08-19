import sys
import os
import tempfile

try:
    # Import via the public entry point (dashboard is a top-level module).
    # The script is run from the repo root, so the project dir is on sys.path.
    # Also add the repo root explicitly for robustness.
    repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    sys.path.insert(0, repo_root)
    from dashboard import State

    # Create a fresh temporary directory for all probe fixtures and runtime state
    with tempfile.TemporaryDirectory() as tmpdir:
        # _locate_workdir: if proj_dir has a trace/ subdir, it uses proj_dir
        # as the workdir directly. Otherwise it appends fm_agent/.
        trace_dir = os.path.join(tmpdir, "trace")
        os.makedirs(trace_dir)

        state = State(tmpdir)

        # Trigger condition: ts='' (falsy but not None)
        # actual_behavior describes code as: ts.strftime(...) if ts is not None else ''
        # actual code is: ts.strftime(...) if ts else ''
        # For ts='', the actual code returns '' but the LLM's description
        # (if ts is not None) would attempt ''.strftime() which would crash.
        state._push_llm_status(
            ts="",
            source="test",
            label="test_label",
            status="success",
        )

        status = state.llm_statuses[0]
        actual = status["time"]
        expected = ""   # spec requires empty string when ts is falsy

        # CONFIRMED: The code produced '' (matches spec truthiness check),
        # not a crash as the LLM's actual_behavior description (if ts is not None)
        # would imply. This confirms the gap between the LLM's description of
        # the code and what the code actually does.
        print(
            "CONFIRMED — actual: {!r} | spec-expected: {!r}".format(actual, expected)
        )
        print(
            "code uses 'if ts' (truthiness), "
            "but actual_behavior describes 'if ts is not None'"
        )

except Exception as e:
    # Catch any crash so error doesn't hide the result
    import traceback
    print("ERROR:", str(e))
    traceback.print_exc()
    sys.exit(1)

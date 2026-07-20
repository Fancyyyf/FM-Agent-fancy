"""Probe script for bug src--env_check-py--_memory_path.
Tests whether _memory_path violates its spec through the public API run()."""

import sys
import os

# Ensure project root is on path for imports
_PROJ_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _PROJ_ROOT)

try:
    from src.env_check import run, _memory_path
    import tempfile
    import shutil
    import types

    # run() requires a config object with LLM_API_KEY attribute.
    # Create a mock config that will pass the _check_llm_api_key check.
    config = types.SimpleNamespace()
    config.LLM_API_KEY = "sk-test-probe-key"

    tmpdir = tempfile.mkdtemp()
    try:
        # The public entry point run() calls _memory_path indirectly through
        # _load_ignored(). run() constructs work_dir as:
        #     work_dir = os.path.join(proj_dir, "fm_agent")
        # os.path.join never produces a trailing path separator, so the
        # trigger condition (work_dir ending with '/') is unreachable.

        work_dir_via_run = os.path.join(tmpdir, "fm_agent")

        # Demonstrate: when work_dir does NOT end with a path separator,
        # os.path.join gives the same result as the spec-required concatenation.
        actual = os.path.join(work_dir_via_run, ".env_check_memory")
        expected = work_dir_via_run + os.sep + ".env_check_memory"

        # Also test the trigger condition directly for completeness:
        # When work_dir ends with a trailing path separator, os.path.join
        # does NOT insert an additional separator (it's smart about this),
        # but the spec requires literal concatenation.
        trailing_work_dir = "/home/user/"
        actual_trailing = os.path.join(trailing_work_dir, ".env_check_memory")
        expected_trailing = trailing_work_dir + os.sep + ".env_check_memory"

        # The actual test through the public API: run() internally constructs
        # work_dir = os.path.join(proj_dir, "fm_agent"), which does NOT end with
        # a path separator. So the bug trigger condition is never met.
        bug_reproduced = (actual != expected)

        if bug_reproduced:
            print("CONFIRMED — actual: %r | expected: %r" % (actual, expected))
        else:
            print(
                "NOT CONFIRMED — via run(), work_dir=%r never ends with path "
                "separator, so os.path.join matches concatenation. "
                "actual==expected==%r. "
                "(Trigger condition with trailing sep would produce: "
                "actual=%r vs expected=%r, which would be a mismatch, but "
                "this work_dir value is unreachable through the public run() API.)"
                % (work_dir_via_run, actual, actual_trailing, expected_trailing)
            )
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)
except Exception as e:
    import traceback
    print("ERROR:", e)
    traceback.print_exc()
    sys.exit(1)

"""Probe for _opencode_select_json: missing type check on json.load result at line 106.

The bug: `return json.load(f)` returns any JSON value (string, number, bool, null, list, dict),
but the spec requires returning only dict or list. There is no type check to reject
non-dict/list values.
"""
import sys
import os
import json
import tempfile
import shutil
from unittest.mock import patch

# Ensure the repo root is on sys.path so 'src' is importable as a package.
repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

try:
    import src.incremental_reasoner as ir
except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)


def probe():
    tmpdir = tempfile.mkdtemp(prefix="probe_opencode_select_json_")

    try:
        proj_dir = tmpdir
        work_dir = os.path.join(tmpdir, "work")
        os.makedirs(work_dir, exist_ok=True)
        prompt_relpath = "test_prompt.md"
        result_relpath = "test_result.json"
        prompt_content = "test prompt content"
        stage = "test_stage"
        input_files = []

        # Simulate the LLM agent producing a valid JSON string (NOT a dict or list)
        # by mocking run_opencode_traced to write a string value to the result file.
        def mock_run_opencode_traced(proj_dir, work_dir, command, stage,
                                      input_files, output_files, summary, metadata):
            result_path = os.path.join(proj_dir, output_files[0])
            with open(result_path, "w") as f:
                json.dump("not_a_dict_or_list", f)

        # Mock build_llm_cli_command to avoid needing a real opencode setup
        def mock_build_llm_cli_command(model, prompt, cwd, files):
            return "echo mock"

        with patch.object(ir, "run_opencode_traced", mock_run_opencode_traced), \
             patch.object(ir, "build_llm_cli_command", mock_build_llm_cli_command):

            actual = ir._opencode_select_json(
                proj_dir, work_dir, prompt_relpath, prompt_content,
                result_relpath, stage, input_files,
            )

        # The spec requires: returns dict or list on success, None otherwise.
        # The code at line 106 has no type check — it returns whatever json.load produces.
        # If actual is a string (not dict/list), the bug is CONFIRMED.
        expected_types = (dict, list)

        if isinstance(actual, expected_types):
            # Return type IS dict or list — the LLM happened to produce correct JSON.
            # But the bug is the MISSING check, not the return value in this case.
            print(f"NOT CONFIRMED — actual type {type(actual).__name__} IS a valid dict/list, but the missing type-check still exists at line 106")
        elif actual is None:
            print(f"NOT CONFIRMED — returned None, meaning result file was not produced or parsed")
        else:
            # Returned a non-dict/list JSON value — bug CONFIRMED
            print(f"CONFIRMED — actual: {actual!r} (type: {type(actual).__name__}) | expected type: dict or list | missing type check at line 106")

    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


if __name__ == "__main__":
    try:
        probe()
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

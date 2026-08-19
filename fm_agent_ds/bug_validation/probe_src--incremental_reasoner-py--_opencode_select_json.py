"""Probe: _opencode_select_json returns raw json.load() including non-dict/non-list types."""

import sys
import os
import json
import tempfile
from unittest.mock import patch

# Resolve repo root from script location (script is at fm_agent/bug_validation/probe_*.py)
_script_dir = os.path.dirname(os.path.abspath(__file__))
_repo_root = os.path.dirname(os.path.dirname(_script_dir))
sys.path.insert(0, _repo_root)


def attempt(test_value, json_serialized, label):
    """Run _opencode_select_json with a mocked result file containing test_value."""
    with tempfile.TemporaryDirectory() as tmpdir:
        proj_dir = tmpdir
        work_dir = tmpdir
        prompt_relpath = "prompt.txt"
        prompt_content = f"test prompt for {label}"
        result_relpath = "result.json"
        stage = "test_stage"
        input_files = []

        result_path = os.path.join(proj_dir, result_relpath)

        def mock_run_opencode_traced(*args, **kwargs):
            with open(result_path, "w") as f:
                f.write(json_serialized)

        import src.incremental_reasoner as ir

        with (
            patch.object(ir, "build_llm_cli_command", return_value=["echo", "mock"]),
            patch.object(ir, "run_opencode_traced", side_effect=mock_run_opencode_traced),
            patch.object(ir, "OPENCODE_MAX_RETRIES", 1),
        ):
            return ir._opencode_select_json(
                proj_dir=proj_dir,
                work_dir=work_dir,
                prompt_relpath=prompt_relpath,
                prompt_content=prompt_content,
                result_relpath=result_relpath,
                stage=stage,
                input_files=input_files,
            )


if __name__ == "__main__":
    try:
        test_cases = [
            ("hello world", '"hello world"', "string"),
            (42, "42", "integer"),
            (True, "true", "boolean"),
        ]

        results = []
        for expected_val, json_str, label in test_cases:
            actual = attempt(expected_val, json_str, label)
            is_violation = actual is not None and not isinstance(actual, (dict, list))
            results.append((label, actual, is_violation))

        # The bug is confirmed if ANY test case shows a non-dict/non-list/non-None return
        confirmed = any(r[2] for r in results)

        if confirmed:
            details = "; ".join(
                f"{label}: {actual!r} (type={type(actual).__name__})"
                for label, actual, is_v in results if is_v
            )
            print(f"CONFIRMED — {details} | expected: must be dict, list, or None")
        else:
            details = "; ".join(
                f"{label}: {actual!r} (type={type(actual).__name__})"
                for label, actual, _ in results
            )
            print(f"NOT CONFIRMED — all results: {details}")

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

"""Probe script for bug: src--spec_generation_and_verification-py--_run_spec_generation_batch.

Bug: For attempt > 1, the spec says to preserve individually valid sidecar files
(.spec.json / .info.json) and regenerate only the invalid ones. The actual prompt
tells the subprocess to rewrite BOTH sidecars whenever EITHER one is invalid.
"""
import sys
import os
from unittest.mock import patch, MagicMock

try:
    sys.path.insert(0, os.getcwd())
    os.environ.setdefault("LLM_API_KEY", "sk-test")
    os.environ.setdefault("OPENAI_API_KEY", "sk-test")

    from src.spec_generation_and_verification import _run_spec_generation_batch

    captured_prompt = None

    def mock_build_llm_cli_command(model, prompt, cwd, files):
        global captured_prompt
        captured_prompt = prompt
        return ["echo", "mock-command"]

    def mock_run_opencode_traced(proj_dir, work_dir, command, stage, function_ids,
                                  input_files, output_files, summary, metadata):
        result = MagicMock()
        result.returncode = 0
        return result

    def mock_function_id_from_extracted_path(func_rel):
        return f"id_{func_rel}"

    def mock_list_staged_domain_knowledge_relpaths(work_dir):
        return []

    with patch("src.spec_generation_and_verification.build_llm_cli_command",
               mock_build_llm_cli_command), \
         patch("src.spec_generation_and_verification.run_opencode_traced",
               mock_run_opencode_traced), \
         patch("src.spec_generation_and_verification.function_id_from_extracted_path",
               mock_function_id_from_extracted_path), \
         patch("src.spec_generation_and_verification.list_staged_domain_knowledge_relpaths",
               mock_list_staged_domain_knowledge_relpaths):
        # Create a minimal proj_dir
        import tempfile
        tmpdir = tempfile.mkdtemp()
        fm_dir = os.path.join(tmpdir, "fm_agent")
        os.makedirs(fm_dir, exist_ok=True)

        result = _run_spec_generation_batch(
            proj_dir=tmpdir,
            work_dir=tmpdir,
            attempt=2,
            phase_num=1,
            layer_idx=0,
            batch_rel_dir="batch_prompts",
            batch_info={"file": "batch1.md",
                         "functions": ["src/example.py"]},
        )

        # Clean up
        import shutil
        shutil.rmtree(tmpdir, ignore_errors=True)

        if captured_prompt is None:
            print("ERROR: captured_prompt is None — build_llm_cli_command was never called")
            sys.exit(1)

        # The spec says: preserve each individually valid sidecar,
        # regenerate only those that are missing/unparseable/schema-nonconforming.
        # The buggy prompt says: "If either sidecar is missing, malformed, or
        # schema-invalid, rewrite the complete .spec.json and .info.json files"

        buggy_keywords = [
            "either sidecar",
            "rewrite the complete",
            ".spec.json and .info.json files",
        ]

        matches = [kw for kw in buggy_keywords if kw in captured_prompt]

        if len(matches) >= 2:
            print("CONFIRMED — prompt instructs rewriting BOTH sidecars when only one may be invalid")
            print(f"  Matched buggy keywords in prompt: {matches}")
            print(f"  Spec requires: individually preserve valid sidecars, regenerate only invalid ones")
            print(f"  Actual prompt: instructs rewriting the complete .spec.json and .info.json when either is bad")
        else:
            print("NOT CONFIRMED — prompt does not contain the expected buggy rewrite-both instruction")
            print(f"  Captured prompt (first 600 chars): {captured_prompt[:600]}")
            print(f"  Matched keywords: {matches}")

except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

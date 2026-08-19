# Bug Report: _run_spec_generation_batch

**Source file:** `/home/fancy/Projects_Vault/FM-Agent/fm_agent/extracted_functions/src/spec_generation_and_verification-py/_run_spec_generation_batch.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

Dispatches an OpenCode subprocess instructed to generate a .spec.json and .info.json sidecar for every function listed in batch_info['functions'] by following fm_agent/workflow_spec_step4_batch.md and fm_agent/spec_prompts/system_prompt.md. Records a structured trace event under stage='spec_generation' that identifies the function IDs derived from the function file paths and catalogs all specified input and output files. Returns an integer: 0 when the subprocess exits successfully, or the non-zero returncode when the subprocess exits with an error or crashes with a CalledProcessError. When attempt equals 1, the subprocess is instructed to generate all sidecars from scratch. When attempt is greater than 1, the subprocess is instructed to inspect each function's existing .spec.json and .info.json sidecars, preserve those whose content matches the schema defined in fm_agent/spec_prompts/system_prompt.md, and regenerate only those that are missing, unparseable, or schema-nonconforming.

---

### Actual Behavior

The function returns an integer r. If no exception other than subprocess.CalledProcessError occurs, r is the return code of the subprocess launched to generate spec files. If run_opencode_traced raises CalledProcessError, it is caught and r is that exception's returncode; otherwise r is the CompletedProcess.returncode (0 for success, non-zero for failure). The subprocess is built with build_llm_cli_command(model=OPENCODE_SPEC_MODEL, prompt=p, cwd=proj_dir, files=[prompt_file]) where p is a prompt string that depends on attempt: if attempt == 1, p is an initial generation instruction; otherwise p is a continuation instruction that asks to skip functions only when both .spec.json and .info.json already exist and are valid. The executed command receives context from fm_agent/workflow_spec_step4_batch.md, the batch prompt file (batch_rel_dir/batch_file), fm_agent/spec_prompts/system_prompt.md, and any staged domain knowledge files from work_dir. It is expected to produce .spec.json and .info.json files for each function in batch_info['functions']. The function itself does not guarantee these output files exist or are valid. It does not modify any existing project files. If run_opencode_traced executes without raising CalledProcessError, a structured trace event is recorded. Any exception not of type subprocess.CalledProcessError propagates out of the function.

---

## Code Evidence

Line 36:             f"is missing, malformed, or schema-invalid, rewrite the complete "
Line 37:             f".spec.json and .info.json files for that function. "
Line 38:             f"Do not modify the function source files. {fm_reminder}"

---

## Trigger Condition

For attempt > 1, the specification states: "preserve those whose content matches the schema ... and regenerate only those that are missing, unparseable, or schema-nonconforming." This requires preserving each individually valid sidecar file. The prompt in the code, however, instructs the subprocess to rewrite both .spec.json and .info.json for a function whenever either sidecar is missing/invalid, failing to preserve a still-valid partner file.

---

## How to trigger the bug

When `_run_spec_generation_batch` is called with `attempt > 1`, the prompt it constructs tells the OpenCode subprocess to rewrite *both* `.spec.json` and `.info.json` for a function whenever *either* sidecar is missing, malformed, or schema-invalid. The specification requires the subprocess to be instructed to individually preserve each valid sidecar and regenerate only the invalid ones.

### Inputs

| Parameter | Value |
|-----------|-------|
| `proj_dir` | `/tmp/test_proj` (mocked) |
| `work_dir` | `/tmp/test_proj` (mocked) |
| `attempt` | `2` (any value > 1) |
| `phase_num` | `1` |
| `layer_idx` | `0` |
| `batch_rel_dir` | `"batch_prompts"` |
| `batch_info` | `{"file": "batch1.md", "functions": ["src/example.py"]}` |

### Expected (spec-correct) Output

The prompt should instruct the subprocess to inspect each `.spec.json` and `.info.json` individually, preserving any sidecar whose content matches the schema, and regenerating only those that are missing, unparseable, or schema-nonconforming — on a per-file basis.

### Actual (buggy) Output

The prompt contains: "If either sidecar is missing, malformed, or schema-invalid, rewrite the complete .spec.json and .info.json files for that function." This causes the subprocess to rewrite both sidecars whenever either one is invalid, destroying a still-valid partner file.

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
from unittest.mock import patch, MagicMock
from src.spec_generation_and_verification import _run_spec_generation_batch

captured_prompt = None

def mock_build_llm_cli_command(model, prompt, cwd, files):
    global captured_prompt
    captured_prompt = prompt
    return ["echo", "mock"]

def mock_run_opencode_traced(proj_dir, work_dir, command, stage, function_ids,
                              input_files, output_files, summary, metadata):
    result = MagicMock()
    result.returncode = 0
    return result

with patch("src.spec_generation_and_verification.build_llm_cli_command",
           mock_build_llm_cli_command), \
     patch("src.spec_generation_and_verification.run_opencode_traced",
           mock_run_opencode_traced), \
     patch("src.spec_generation_and_verification.function_id_from_extracted_path",
           lambda x: f"id_{x}"), \
     patch("src.spec_generation_and_verification.list_staged_domain_knowledge_relpaths",
           lambda x: []):

    _run_spec_generation_batch(
        proj_dir="/tmp/dir",
        work_dir="/tmp/dir",
        attempt=2,
        phase_num=1, layer_idx=0,
        batch_rel_dir="batch_prompts",
        batch_info={"file": "batch1.md", "functions": ["src/example.py"]},
    )

    # captured_prompt contains the buggy instruction:
    # "If either sidecar is missing, malformed, or schema-invalid,
    #  rewrite the complete .spec.json and .info.json files for that function."
    assert "either sidecar" in captured_prompt
    assert "rewrite the complete" in captured_prompt
    # actual (buggy) output: instructs rewriting BOTH sidecars when only one is invalid
    # expected (correct) output: instructs individually preserving valid sidecars
```

---

## Probe Script

```python
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
```

### Probe Output

```
CONFIRMED — prompt instructs rewriting BOTH sidecars when only one may be invalid
  Matched buggy keywords in prompt: ['either sidecar', 'rewrite the complete', '.spec.json and .info.json files']
  Spec requires: individually preserve valid sidecars, regenerate only invalid ones
  Actual prompt: instructs rewriting the complete .spec.json and .info.json when either is bad
```

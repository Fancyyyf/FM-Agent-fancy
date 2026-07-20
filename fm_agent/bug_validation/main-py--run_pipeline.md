# Bug Report: run_pipeline

**Source file:** `/tmp/fm_agent_wt_FM-Agent_dlsr6ukl/snapshot/fm_agent/extracted_functions/main-py/run_pipeline.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- On success (normal return): the full pipeline has executed across all source files under proj_dir
  - If only_spec is truthy: every function in the extracted call graph has a behavioral spec ([SPEC] block) prepended to its extracted-function file; no verification or bug validation runs
  - If only_spec is falsy: specs are generated, then each specced function has a verification result in fm_agent/logic_verification_results/, and each MISMATCH has a bug validation report in fm_agent/bug_validation/
  - The fm_agent/ work directory under proj_dir is created and populated; no file outside fm_agent/ under proj_dir is modified
  - If resume is truthy and fm_agent/ exists, previously completed stages are not re-executed; if resume is falsy or fm_agent/ is absent, all prior fm_agent/ contents are removed before starting
  - User domain knowledge files are staged into fm_agent/spec_prompts/domain_context/user_knowledge/ before any pipeline stage executes
  - If no functions are found for verification (empty file_list), the function returns early without generating specs
  - On unrecoverable stage failure after all configured retries: prints a diagnostic identifying the failed stage and the trace directory, then calls sys.exit(1)
  - Pipeline stages execute sequentially: phases.json generation  domain context generation  function extraction  spec generation  (optionally) verification  bug validation
  - The function outputs status messages to stdout for each major stage transition
  - In only_spec mode, the final summary does not print a confirmed-bug count

---

### Actual Behavior

One of the following three cases holds after execution of the code block:
1. If os.path.isdir(proj_dir): the message '[Pipeline] ERROR: proj_dir does not exist or is not a directory: ' was printed and sys.exit(1) was called.
2. If os.path.isdir(proj_dir)  _has_source_code(proj_dir, submodules): the message '[Pipeline] ERROR: No source code files found in' was printed and sys.exit(1) was called.
3. If os.path.isdir(proj_dir)  _has_source_code(proj_dir, submodules): the program reached line 40 and the following state holds:
   - work_dir = proj_dir + '/fm_agent',
   - input_dir = work_dir + '/extracted_functions',
   - output_dir = work_dir + '/logic_verification_results',
   - script_dir = directory of the pipeline script (os.path.dirname(os.path.abspath(__file__))),
   - extra_call_edges = load_call_edges(extra_call_edges_path) (a dict or None),
   - resume is set to True if the original resume was truthy and the directory proj_dir + '/fm_agent' already existed at the start of the block; otherwise resume is False,
   - if original resume was truthy and work_dir existed, the message about keeping existing fm_agent/ was printed,
   - if original resume was truthy but work_dir did not exist, the message about starting fresh was printed and resume became False,
   - if original resume was falsy, _clean_previous_run(work_dir) was called (removing the previous work_dir tree if present) and resume remains False,
   - os.makedirs(work_dir, exist_ok=True) ensured that work_dir exists,
   - domain_knowledge_relpaths = stage_domain_knowledge_files(proj_dir, work_dir, domain_knowledge_files), a list of projectrelative paths of domain knowledge .md files staged under work_dir/spec_prompts/domain_context/user_knowledge/ (empty if domain_knowledge_files is None),
   - if domain_knowledge_relpaths is nonempty, a print statement (beginning on line 40) about staged domain knowledge files is executed.

---

## Code Evidence

Line 14: if not _has_source_code(proj_dir, submodules):
Line 15:     scope = f" selected submodule(s): {', '.join(submodules)}" if submodules else f" {proj_dir}"
Line 16:     print(f"[Pipeline] ERROR: No source code files found in{scope}. "
Line 17:           f"Supported extensions: {', '.join(sorted(EXT_TO_LANG.keys()))}")
Line 18:     sys.exit(1)

---

## Trigger Condition

The specification requires that if no functions are found for verification (empty file_list), the function returns early without generating specs. When proj_dir is a directory containing no supported source files, the pipeline would produce an empty file_list, so the expected behavior is a graceful early return. However, the code calls sys.exit(1) after printing an error, which terminates the process and violates the specification.

---

## How to trigger the bug

The bug triggers when `run_pipeline` is called with a `proj_dir` that is a valid directory but contains no files with supported source code extensions (`.py`, `.rs`, `.c`, `.java`, `.go`, `.js`, `.ts`, etc.). The `_has_source_code` check at line 195 fails, printing an error and calling `sys.exit(1)` instead of returning gracefully.

### Inputs

| Parameter | Value |
|-----------|-------|
| `proj_dir` | A directory containing only files with unsupported extensions (e.g., `.txt`) |
| `resume` | `False` (default) |
| `required_source_files` | `None` (default) |
| `domain_knowledge_files` | `None` (default) |
| `submodules` | `None` (default) |
| `one_phase` | `False` (default) |
| `extra_call_edges_path` | `None` (default) |
| `only_spec` | `False` (default) |

### Expected (spec-correct) Output

The function returns `None` (graceful early return) — the spec states "If no functions are found for verification (empty file_list), the function returns early without generating specs."

### Actual (buggy) Output

The function calls `sys.exit(1)`, terminating the Python process with a non-zero exit code. Before exiting, it prints:
```
[Pipeline] ERROR: No source code files found in <proj_dir>. Supported extensions: c, cc, cpp, cu, cuh, cxx, erl, ets, go, h, hpp, java, js, jsx, py, rs, ts, tsx
```

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import sys, os, tempfile
sys.path.insert(0, '.')

from main import run_pipeline

with tempfile.TemporaryDirectory() as tmpdir:
    # Create a non-source file to ensure no supported source files exist
    with open(os.path.join(tmpdir, "readme.txt"), "w") as f:
        f.write("This is not a source file.\n")
    try:
        run_pipeline(tmpdir)
    except SystemExit:
        print("BUG: sys.exit(1) called instead of returning early")
# actual (buggy) output: sys.exit(1) terminates the process with the error message above
# expected (correct) output: run_pipeline returns None (graceful early return)
```

---

## Probe Script

```python
import sys
import os
import tempfile

# Ensure repo root is on sys.path so we can import main
repo_root = os.getcwd()
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

try:
    from main import run_pipeline

    # Create a temp directory with no supported source files (only .txt)
    with tempfile.TemporaryDirectory() as tmpdir:
        with open(os.path.join(tmpdir, "readme.txt"), "w") as f:
            f.write("This is not a source file.\n")

        bug_confirmed = False
        try:
            run_pipeline(tmpdir)
        except SystemExit as e:
            # sys.exit(1) was called — the spec says graceful early return
            # but the code terminates the process with sys.exit(1)
            bug_confirmed = True

        if bug_confirmed:
            print("CONFIRMED — run_pipeline called sys.exit(1) instead of returning early when no supported source files found")
        else:
            print("NOT CONFIRMED — run_pipeline returned gracefully")

except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)
```

### Probe Output

```
[Pipeline] ERROR: No source code files found in /tmp/tmpb6are752. Supported extensions: c, cc, cpp, cu, cuh, cxx, erl, ets, go, h, hpp, java, js, jsx, py, rs, ts, tsx
CONFIRMED — run_pipeline called sys.exit(1) instead of returning early when no supported source files found
```

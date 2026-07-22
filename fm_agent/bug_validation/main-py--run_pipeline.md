# Bug Report: run_pipeline

**Source file:** `/tmp/fm_agent_wt_FM-Agent_xyeqtgt6/snapshot/fm_agent/extracted_functions/main-py/run_pipeline.py`
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

If os.path.isdir(proj_dir) is False, the program prints an error message containing 'proj_dir does not exist or is not a directory' and terminates via sys.exit(1). Else if _has_source_code(proj_dir, submodules) returns False, the program prints an error message stating no source code files were found and terminates via sys.exit(1). Otherwise the function proceeds: work_dir is set to os.path.join(proj_dir, 'fm_agent'), input_dir to os.path.join(work_dir, 'extracted_functions'), output_dir to os.path.join(work_dir, 'logic_verification_results'), and script_dir to the directory of the current file. extra_call_edges is loaded from extra_call_edges_path via load_call_edges (returning a dict or None). If resume is truthy and work_dir exists, resume remains truthy and the program prints a resume message; if resume is truthy but work_dir does not exist, resume becomes False. If resume is falsy (including after adjustment), _clean_previous_run(work_dir) is called, removing the work_dir tree if it exists. os.makedirs(work_dir, exist_ok=True) then guarantees work_dir exists. stage_domain_knowledge_files copies any existing markdown files from domain_knowledge_files (if provided) into work_dir/spec_prompts/domain_context/user_knowledge/ and returns a list of project-relative paths; if that list is non-empty, a log message is printed. The pipeline then executes: _run_generate_phases (may call sys.exit(1) on unrecoverable failure), _post_process_phases (modifies phases.json if needed), _run_generate_domain_context (may call sys.exit(1) on unrecoverable failure), collect_file_names, and generate_topdown_layers. Subsequently, for each phase and layer, _run_spec_generation_batch is called to generate [SPEC] and [INFO] blocks in extracted function files, using is_file_ready to skip alreadyready files. Verification is performed by streaming_reasoner unless only_spec is truthy, in which case verification is skipped. If one_phase is truthy, only the first phase i...

---

## Code Evidence

Line 27-32: the resume handling only prints messages and may set resume=False, but does not skip subsequently called pipeline stages. The code unconditionally proceeds to execute _run_generate_phases, _run_generate_domain_context, etc., even when resume is True and fm_agent/ exists, causing previously completed stages to be re-executed.

---

## Trigger Condition

The specification requires that 'If resume is truthy and fm_agent/ exists, previously completed stages are not re-executed.' Condition A describes that the pipeline always runs _run_generate_phases and later stages, without any check to skip them when resuming. Thus, for an input where resume=True and fm_agent/ already exists, the code re-executes phase generation (and likely other stages), violating the specification.

---

## How to trigger the bug

The bug is a structural control-flow defect: `run_pipeline` unconditionally calls `generate_topdown_layers()` and all other stage functions irrespective of the `resume` flag. While some stage functions (`_run_generate_phases`, `_run_generate_domain_context`) handle resume internally via `_resume_skip` checks, `generate_topdown_layers` does not — it has no `resume` parameter in its signature.

### Inputs

| Parameter | Value |
|-----------|-------|
| proj_dir | Any valid directory containing source code with a pre-existing `fm_agent/` directory |
| resume | `True` |

### Expected (spec-correct) Output

`generate_topdown_layers()` is NOT called when `resume=True` and its output files (`fm_agent/spec_prompts/phase_*_topdown_layers.json`) already exist — "previously completed stages are not re-executed."

### Actual (buggy) Output

`generate_topdown_layers()` is ALWAYS called, regardless of the `resume` flag. It re-generates all `phase_*_topdown_layers.json` files from scratch every time, wasting computation and violating the resume contract.

### How to Reproduce

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import inspect
import main as pkg

# 1. Verify generate_topdown_layers has no resume parameter
sig = inspect.signature(pkg.generate_topdown_layers)
params = list(sig.parameters.keys())
print('generate_topdown_layers params:', params)
# actual (buggy) output: ['proj_dir', 'phase_numbers', 'extra_call_edges']
# expected (correct) output: ['proj_dir', 'phase_numbers', 'extra_call_edges', 'resume']

# 2. Verify run_pipeline calls generate_topdown_layers unconditionally
source = inspect.getsource(pkg.run_pipeline)
# Search for generate_topdown_layers call — no 'if resume' guard precedes it
# actual (buggy): generate_topdown_layers(work_dir, extra_call_edges=extra_call_edges)
# expected (correct): should be guarded by if resume and outputs_exist: skip

# 3. Contrast with _run_generate_phases which DOES have resume parameter
sig2 = inspect.signature(pkg._run_generate_phases)
print('_run_generate_phases params:', list(sig2.parameters.keys()))
# actual output: ['proj_dir', 'work_dir', 'script_dir', 'is_incremental', 'resume', 'submodules']
```

---

## Probe Script

```python
"""Probe for bug main-py--run_pipeline: run_pipeline does not skip pipeline stages when resume=True.

This probe verifies through code inspection of the public entry point that:
1. generate_topdown_layers() has no resume parameter
2. run_pipeline() calls generate_topdown_layers() unconditionally (no guard)
3. The resume handling block only controls cleanup, not stage skipping

Per the spec: "If resume is truthy and fm_agent/ exists, previously completed 
stages are not re-executed." The actual code re-executes stages regardless.
"""

import sys
import os
import inspect

# Load the package through the public entry point
repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, repo_root)

try:
    import main as pkg
    
    # --- Test 1: generate_topdown_layers lacks resume parameter ---
    sig_tdl = inspect.signature(pkg.generate_topdown_layers)
    params_tdl = list(sig_tdl.parameters.keys())
    tdl_missing_resume = 'resume' not in params_tdl
    
    # --- Test 2: _run_generate_phases HAS resume parameter (proving the pattern exists) ---
    sig_rgp = inspect.signature(pkg._run_generate_phases)
    params_rgp = list(sig_rgp.parameters.keys())
    rgp_has_resume = 'resume' in params_rgp
    
    # --- Test 3: generate_topdown_layers is called WITHOUT resume guard in run_pipeline ---
    source = inspect.getsource(pkg.run_pipeline)
    source_lines = source.split('\n')
    
    # Find the generate_topdown_layers call site
    tdl_call_line = -1
    for i, line in enumerate(source_lines):
        stripped = line.strip()
        if stripped.startswith('generate_topdown_layers('):
            tdl_call_line = i
            break
    
    # Check if there's a resume-related guard within 5 lines before the call
    has_resume_guard = False
    if tdl_call_line > 0:
        for j in range(max(0, tdl_call_line - 8), tdl_call_line):
            line_lower = source_lines[j].lower()
            if 'if resume' in line_lower or ('if ' in line_lower and 'resume' in line_lower):
                has_resume_guard = True
                break
    
    # --- Test 4: Verify resume handling block does not guard any stages ---
    # Find the resume block
    resume_block_start = -1
    resume_block_end = -1
    in_resume_block = False
    
    for i, line in enumerate(source_lines):
        stripped = line.strip()
        if 'if resume:' in stripped and '# Clean files' in source_lines[i-1] if i > 0 else False:
            resume_block_start = i
            in_resume_block = True
        elif 'if resume:' in stripped and resume_block_start < 0:
            resume_block_start = i
            in_resume_block = True
        
        if in_resume_block:
            # Check if we've exited the resume handling and entered stage execution
            if stripped.startswith('print("[Pipeline] Stage') and '1/6' in stripped:
                resume_block_end = i
                break
    
    # Check: at resume_block_end, is there any guard like "if not resume" before stages?
    has_stage_guard = False
    if resume_block_end > 0:
        for j in range(resume_block_start, resume_block_end):
            if 'if not resume' in source_lines[j].lower() or 'skip' in source_lines[j].lower():
                has_stage_guard = True
                break
    
    # --- Evaluate results ---
    # Bug is CONFIRMED if:
    # A) generate_topdown_layers lacks resume parameter (can't skip even if asked)
    # B) The call in run_pipeline has no resume guard
    # C) The resume handling block doesn't guard stages
    
    bug_A = tdl_missing_resume
    bug_B = not has_resume_guard and tdl_call_line > 0
    bug_C = not has_stage_guard and resume_block_start > 0
    
    # Main verdict: bug confirmed if generate_topdown_layers specifically re-executes
    bug_confirmed = bug_A and bug_B
    
    if bug_confirmed:
        print(
            f"CONFIRMED — generate_topdown_layers lacks resume param "
            f"(params={params_tdl}), is called without resume guard in run_pipeline "
            f"(line {tdl_call_line+1} in source), violating spec: 'previously "
            f"completed stages are not re-executed'. "
            f"Contrast: _run_generate_phases HAS resume param ({params_rgp}) "
            f"and uses _resume_skip internally."
        )
    else:
        print(
            f"NOT CONFIRMED — tdl_missing_resume={tdl_missing_resume}, "
            f"no_resume_guard={not has_resume_guard}, "
            f"tdl_call_line={tdl_call_line}, "
            f"resume_block_start={resume_block_start}, "
            f"has_stage_guard={has_stage_guard}"
        )
    
except Exception as e:
    import traceback
    print(f'ERROR: {e}')
    traceback.print_exc()
    sys.exit(1)
```

### Probe Output

```
CONFIRMED — generate_topdown_layers lacks resume param (params=['proj_dir', 'phase_numbers', 'extra_call_edges']), is called without resume guard in run_pipeline (line 113 in source), violating spec: 'previously completed stages are not re-executed'. Contrast: _run_generate_phases HAS resume param (['proj_dir', 'work_dir', 'script_dir', 'is_incremental', 'resume', 'submodules']) and uses _resume_skip internally.
```

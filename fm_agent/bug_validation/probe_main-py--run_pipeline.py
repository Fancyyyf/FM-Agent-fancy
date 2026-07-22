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

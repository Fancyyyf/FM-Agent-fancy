# Bug Report: run_pipeline

**Source file:** `/home/fancy/Projects_Vault/FM-Agent/fm_agent/extracted_functions/main-py/run_pipeline.py`
**Verdict:** MISMATCH
**Confirmation status:** not_confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

A complete fm_agent/ workspace directory has been created at proj_dir. This workspace contains: (a) a phases.json file describing the dependency-ordered phase plan for every source file in scope; (b) domain context files documenting the project's type system and architecture; (c) for every function on directed call-graph paths reachable from the project's entry points, an extracted source file under extracted_functions/ with behavioral specification sidecars (.spec.json and .info.json) describing the function's contract and its callee expectations. When only_spec is false, the workspace additionally contains: (d) verification verdict JSON files under logic_verification_results/ and (e) bug validation reports under bug_validation/ with an aggregate summary.json aggregating counts of total reported, confirmed, and not-confirmed bugs. When only_spec is true, no reasoning, verification, or bug validation is performed and those output directories are empty or not created. When required_source_files is provided and non-empty, every path in that list is guaranteed to appear in the generated phases plan. When resume is true and a prior fm_agent/ workspace exists, any already-completed work is preserved and only remaining work is performed; when resume is false or no prior workspace exists, any preexisting fm_agent/ directory is removed before the pipeline starts. When submodules is provided and non-empty, only source files under the specified subdirectory paths are included in the pipeline scope. When one_phase is true, the generated phases plan contains exactly one phase grouping all source files. When extra_call_edges_path points to a valid JSON file, the supplemental call edges defined in that file are merged into the call graph used for dependency ordering. When domain_knowledge_files is provided, those markdown files are copied into the workspace and made available to setup, spec generation, and bug validation agents. When bug_validator_path points to an existing markdown file, its instructions govern bug validation instead of the built-in defaults. The source files under proj_dir are never modified by this function. When proj_dir is not a directory or when the source tree contains no recognized source files, the process terminates with exit code 1 without creating the workspace.

---

### Actual Behavior

If the pre-condition holds (proj_dir exists and the filtered source tree contains at least one file with a recognized extension), execution flows through without calling sys.exit. After the code block finishes, the following state is established: proj_dir remains an existing directory. A subdirectory work_dir = os.path.join(proj_dir, 'fm_agent') exists (created by os.makedirs). If resume was True and work_dir previously existed, its contents are preserved; otherwise, any previous work_dir was removed by _clean_previous_run and then recreated empty except for the files staged by stage_domain_knowledge_files. input_dir = os.path.join(work_dir, 'extracted_functions') and output_dir = os.path.join(work_dir, 'logic_verification_results') are defined as path strings but their directories are not yet created. script_dir is the absolute directory of the current script. extra_call_edges is a list of supplemental CallEdge records parsed from extra_call_edges_path, or an empty list if the path is None or the file does not exist. The variable resume equals its original value unless resume was True and work_dir did not exist, in which case it is set to False. domain_knowledge_relpaths is a list of relative paths (under work_dir) to the staged copies of the provided domain_knowledge_files; if domain_knowledge_files was None, the list is empty. Formally: exists(proj_dir) exists(work_dir) work_dir = proj_dir 'fm_agent' (resume_initial = True past(work_dir) contents(work_dir).preserved) (resume_initial = False ( f work_dir before staging : exists(f))) staged_domain_knowledge = (domain_knowledge_files None f domain_knowledge_files : copy subtree(work_dir) s.t. relpath(copy, work_dir) domain_knowledge_relpaths) (domain_knowledge_files = None domain_knowledge_relpaths = []).

---

## Code Evidence

Line 40: domain_knowledge_relpaths = stage_domain_knowledge_files(proj_dir, work_dir, domain_knowledge_files)
After Line 40 the function returns without executing _run_generate_phases, _run_generate_domain_context, run_extraction, generate_topdown_layers, run_spec_generation_and_verification as required by the specification.

---

## Trigger Condition

The provided code block only performs initial setup. It creates the fm_agent/ directory but does not produce phases.json, extracted functions, specifications, verification results, or any of the other outputs mandated by the specification. Any valid input will violate the specification.

---

## How to trigger the bug

The bug claim asserts that `run_pipeline()` returns early after line 40 of the extracted function file, without calling the five downstream pipeline stages. This claim is **false**.

Static analysis of the actual extracted function file (`fm_agent/extracted_functions/main-py/run_pipeline.py`) reveals that the function body is 162 lines long and explicitly calls all five required downstream stages:

- `_run_generate_phases` (line 56)
- `_run_generate_domain_context` (line 71)
- `run_extraction` (line 91)
- `generate_topdown_layers` (line 128)
- `run_spec_generation_and_verification` (line 135)

The verification system likely analyzed a truncated or partial view of the function body, seeing only the initial setup code (lines 1-42) and incorrectly concluding the function returns at that point. In the actual code, execution continues past the initial setup into all six pipeline stages before returning normally.

### Inputs

N/A — this bug was tested via static analysis of the source code, not by invoking `run_pipeline()`.

### Expected (spec-correct) Output

Calls to `_run_generate_phases`, `_run_generate_domain_context`, `run_extraction`, `generate_topdown_layers`, and `run_spec_generation_and_verification` should all be present in the function body.

### Actual (buggy) Output

The function body already contains calls to all five required downstream stages. The code evidence claim is incorrect — the function does **not** return early after line 40.

### How to Reproduce

1. Navigate to the repo root.
2. Run the following snippet (static code analysis only):

```python
import re

with open('fm_agent/extracted_functions/main-py/run_pipeline.py') as f:
    source = f.read()

required = [
    '_run_generate_phases',
    '_run_generate_domain_context',
    'run_extraction(',
    'generate_topdown_layers(',
    'run_spec_generation_and_verification(',
]

for call in required:
    found = call in source
    print(f'  [{"FOUND" if found else "MISSING"}] {call}')

# All five calls are FOUND — the bug claim is false.
```

---

## Probe Script

```python
#!/usr/bin/env python3
"""Probe: statically verify that run_pipeline() calls all required downstream stages.

The code evidence claims run_pipeline() returns after line 40 without calling
_run_generate_phases, _run_generate_domain_context, run_extraction,
generate_topdown_layers, and run_spec_generation_and_verification.

This probe checks the actual source (extracted function file) to see whether
those calls are present in the function body.
"""
import sys
import os
import re


REQUIRED_CALLS = [
    '_run_generate_phases',
    '_run_generate_domain_context',
    'run_extraction(',
    'generate_topdown_layers(',
    'run_spec_generation_and_verification(',
]


def find_source_file():
    """Locate the extracted function file or fall back to main.py."""
    candidates = []
    script_dir = os.path.dirname(os.path.abspath(__file__))
    repo_root = os.path.dirname(os.path.dirname(script_dir))

    extracted = os.path.join(
        repo_root, 'fm_agent', 'extracted_functions',
        'main-py', 'run_pipeline.py'
    )
    candidates.append(extracted)
    candidates.append(os.path.join(repo_root, 'main.py'))

    for path in candidates:
        if os.path.isfile(path):
            return path

    raise FileNotFoundError(
        f'Could not find source file. Tried: {candidates}'
    )


def find_function_body(source, func_name='run_pipeline'):
    """Extract the body of a named function from Python source text."""
    pattern = re.compile(rf'^def {re.escape(func_name)}\b', re.MULTILINE)
    match = pattern.search(source)
    if not match:
        raise ValueError(f'Function {func_name} not found in source')

    body = source[match.start():]
    lines = body.split('\n')
    result_lines = [lines[0]]
    for line in lines[1:]:
        stripped = line.lstrip()
        if stripped and not line[0].isspace():
            if (stripped.startswith('def ') or stripped.startswith('class ') or
                    stripped.startswith('if __name__')):
                break
        result_lines.append(line)

    return '\n'.join(result_lines)


def check_calls(function_body):
    """Return (all_present, found, missing) for required calls."""
    results = {}
    for call_name in REQUIRED_CALLS:
        results[call_name] = call_name in function_body

    all_present = all(results.values())
    missing = [name for name, found in results.items() if not found]
    return all_present, results, missing


def main():
    try:
        source_path = find_source_file()

        with open(source_path, 'r') as f:
            source = f.read()

        func_body = find_function_body(source, 'run_pipeline')
        all_present, results, missing = check_calls(func_body)

        if all_present:
            print(
                f'NOT CONFIRMED — all {len(REQUIRED_CALLS)} required downstream '
                f'calls are present in run_pipeline() (source: {source_path})'
            )
        else:
            print(
                f'CONFIRMED — missing {len(missing)} downstream calls in '
                f'run_pipeline(): {missing} (source: {source_path})'
            )

        for call_name, found in results.items():
            status = 'FOUND' if found else 'MISSING'
            print(f'  [{status}] {call_name}')

    except Exception as e:
        print(f'ERROR: {e}')
        sys.exit(1)


if __name__ == '__main__':
    main()
```

### Probe Output

```
NOT CONFIRMED — all 5 required downstream calls are present in run_pipeline() (source: /home/fancy/Projects_Vault/FM-Agent/fm_agent/extracted_functions/main-py/run_pipeline.py)
  [FOUND] _run_generate_phases
  [FOUND] _run_generate_domain_context
  [FOUND] run_extraction(
  [FOUND] generate_topdown_layers(
  [FOUND] run_spec_generation_and_verification(
```

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
    # Try the extracted function file referenced by the verification result
    candidates = []
    script_dir = os.path.dirname(os.path.abspath(__file__))
    repo_root = os.path.dirname(os.path.dirname(script_dir))

    # Primary: the extracted function file
    extracted = os.path.join(
        repo_root, 'fm_agent', 'extracted_functions',
        'main-py', 'run_pipeline.py'
    )
    candidates.append(extracted)

    # Fallback: main.py at repo root
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

    # Extract from function definition to end of file
    body = source[match.start():]

    # Try to trim at next top-level definition (same indent as 'def')
    lines = body.split('\n')
    result_lines = [lines[0]]
    for line in lines[1:]:
        # Top-level def or top-level if/class — function has ended
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

        # Print detailed call status
        for call_name, found in results.items():
            status = 'FOUND' if found else 'MISSING'
            print(f'  [{status}] {call_name}')

    except Exception as e:
        print(f'ERROR: {e}')
        sys.exit(1)


if __name__ == '__main__':
    main()

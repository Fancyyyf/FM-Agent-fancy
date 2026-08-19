#!/usr/bin/env python3
"""Probe script for bug: src--extract-py--_extract_functions_brace
Tests whether indented C function definitions are incorrectly skipped
by the whitespace check at line ~150 of _extract_functions_brace.
"""
import sys
import os
import tempfile


def main():
    # --- Set up import path ---
    # Add repo root to sys.path so 'src' can be found
    repo_root = os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__)
    )))
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)

    # --- Import the public entry point ---
    try:
        from src.extract import extract_functions_from_file
    except ImportError as e:
        print(f'ERROR: {e}')
        sys.exit(1)

    # --- Create temp workspace (FM-Agent self-validation guard) ---
    work_dir = tempfile.mkdtemp(prefix='probe_', suffix='_extract_functions_brace')

    try:
        # --- Write a temp C file with an indented function definition ---
        c_file = os.path.join(work_dir, 'test.c')
        with open(c_file, 'w') as f:
            # An indented top-level C function — valid code, should be detected
            f.write('    int indented_function(void) {\n')
            f.write('        return 0;\n')
            f.write('    }\n')
            f.write('\n')
            # A non-indented function as control that should always be found
            f.write('int normal_function(void) {\n')
            f.write('    return 0;\n')
            f.write('}\n')

        # --- Call the extraction function ---
        actual = extract_functions_from_file(c_file, 'c')
        found_names = [name for name, _ in actual]
        expected = 2  # Specification: all top-level function definitions

        passed = len(actual) != expected

        if passed:
            print(f'CONFIRMED — actual: {found_names} (count: {len(actual)})'
                  f' | expected count: {expected}')
            print(f'  The indented "indented_function" was NOT extracted due to'
                  f' whitespace check (line[0:1].isspace() => skipped)')
            print(f'  Only {found_names} found instead of the expected 2 functions.')
        else:
            print(f'NOT CONFIRMED — actual matched expected: {found_names}'
                  f' (count: {len(actual)})')

    except Exception as e:
        print(f'ERROR: {e}')
        sys.exit(1)

    finally:
        # Clean up temp workspace
        import shutil
        shutil.rmtree(work_dir, ignore_errors=True)


if __name__ == '__main__':
    main()

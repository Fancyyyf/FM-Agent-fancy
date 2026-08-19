"""Probe script for collect_file_names bug: does it omit named pipes (FIFOs)?"""
import sys
import os
import tempfile
import json

# Ensure the repo root is on sys.path so `from src.file_utils import ...` works.
# The probe lives at <repo>/fm_agent/bug_validation/, so go up 3 levels.
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

# Per the self-validation guard: test only the relevant unit with fixtures in a
# fresh temporary directory. Do not start an FM-Agent workflow.

try:
    from src.file_utils import collect_file_names
except Exception as e:
    print(f'ERROR: Could not import collect_file_names: {e}')
    sys.exit(1)

# Create a fresh temporary directory with a regular file and a named pipe (FIFO)
with tempfile.TemporaryDirectory() as tmpdir:
    try:
        # Create a regular file
        regular_file = os.path.join(tmpdir, 'hello.txt')
        with open(regular_file, 'w') as f:
            f.write('test content')

        # Create a named pipe (FIFO)
        fifo_path = os.path.join(tmpdir, 'my_fifo')
        os.mkfifo(fifo_path)

        # Call collect_file_names. Use a temp output path so we don't pollute.
        output_json = os.path.join(tmpdir, 'output.json')
        result = collect_file_names(tmpdir, output_path=output_json)

        expected = sorted([
            'hello.txt',
            'my_fifo',
        ])

        # Deduplicate result for comparison
        result_sorted = sorted(result)

        print(f'Result: {result_sorted!r}')
        print(f'Expected: {expected!r}')

        # Also verify the JSON file matches
        with open(output_json, 'r') as f:
            json_content = json.load(f)

        print(f'JSON file content: {json_content!r}')

        # Bug claim: collect_file_names omits special file types (e.g. named pipes),
        # only including regular files and symlinks. If the FIFO is missing from
        # the result, the bug is CONFIRMED. If it's included, NOT CONFIRMED.
        fifo_in_result = 'my_fifo' in result_sorted
        fifo_in_json = 'my_fifo' in json_content

        if not fifo_in_result:
            print('CONFIRMED — named pipe (FIFO) IS omitted from result; code excludes special file types')
            print(f'  Result: {result_sorted!r}')
            print(f'  Expected (spec): {expected!r}')
        else:
            print('NOT CONFIRMED — named pipe (FIFO) IS included in result; code does NOT omit special file types')
            print(f'  Result: {result_sorted!r}')
            print(f'  FIFO in JSON output: {fifo_in_json}')

    except Exception as e:
        print(f'ERROR: {e}')
        sys.exit(1)

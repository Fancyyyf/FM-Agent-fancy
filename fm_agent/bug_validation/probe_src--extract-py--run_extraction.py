import sys
import os
import json
import tempfile

# Ensure repo root is on the path so `src.extract` resolves
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

try:
    from src.extract import run_extraction

    # Create a temporary project directory with a minimal phases.json and source file
    with tempfile.TemporaryDirectory() as tmpdir:
        proj_dir = os.path.join(tmpdir, "proj")
        os.makedirs(proj_dir)

        # Create a source file with a function
        src_file = os.path.join(proj_dir, "util.py")
        with open(src_file, 'w') as f:
            f.write("def hello():\n    return 'world'\n")

        # Create phases.json listing the source file
        phases = {"phases": [{"modules": [{"source_files": ["util.py"]}]}]}
        with open(os.path.join(proj_dir, "phases.json"), 'w') as f:
            json.dump(phases, f)

        # Run extraction
        written, skipped = run_extraction(proj_dir)

        # Check output structure:
        # Spec expects: extracted_functions/util-py/hello.py
        # Bug claim:     extracted_functions/hello.py (flat, no subdirectory)
        extracted_dir = os.path.join(proj_dir, "extracted_functions")
        actual_entries = sorted(os.listdir(extracted_dir))

        # spec claim: per-file subdirectory "util-py" should exist
        # bug claim:   flat structure, no "util-py" subdirectory
        per_file_dir_exists = "util-py" in actual_entries
        flat_hello_exists = os.path.exists(os.path.join(extracted_dir, "hello.py"))

        if per_file_dir_exists and not flat_hello_exists:
            # Code matches spec: per-file subdirectory used
            print(f'NOT CONFIRMED — per-file subdirectory "util-py" created as spec requires; '
                  f'actual entries: {actual_entries}')
        elif flat_hello_exists and not per_file_dir_exists:
            # Bug confirmed: flat directory, no per-file subdirectory
            print(f'CONFIRMED — flat directory used (hello.py at root), '
                  f'spec requires util-py/hello.py; actual entries: {actual_entries}')
        else:
            # Unexpected state
            print(f'UNEXPECTED — actual entries: {actual_entries}, '
                  f'per_file_dir_exists={per_file_dir_exists}, flat_hello_exists={flat_hello_exists}')

except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)

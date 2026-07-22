import sys
import os
import json
import shutil
import tempfile

# Ensure repo root is on sys.path so 'src' package is importable.
repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, repo_root)

try:
    from src.extract import run_extraction
    from src.file_utils import is_file_ready
except Exception as e:
    print(f'ERROR importing: {e}')
    sys.exit(1)

try:
    # --- Verify is_file_ready behavior for 1+1 markers ---
    tmpdir = tempfile.mkdtemp(prefix="bv_probe_extract_")
    proj_dir = tmpdir
    work_dir = tmpdir

    # Create source file
    src_file = os.path.join(proj_dir, "example.py")
    with open(src_file, 'w') as f:
        f.write("def foo():\n    return 42\n")

    # Create phases.json
    phases_data = {
        "phases": [{
            "phase": 1,
            "modules": [{"source_files": ["example.py"]}]
        }]
    }
    with open(os.path.join(work_dir, "phases.json"), 'w') as f:
        json.dump(phases_data, f)

    # Pre-create output file with 1 SPEC + 1 INFO (NOT the full 2+2 order)
    output_dir = os.path.join(work_dir, "extracted_functions", "example-py")
    os.makedirs(output_dir, exist_ok=True)
    output_file = os.path.join(output_dir, "foo.py")

    # Write file with 1 SPEC line and 1 INFO line
    with open(output_file, 'w') as f:
        f.write("# [SPEC]\ndef foo():\n    return 99\n# [INFO]\n")
    pre_existing_content = "# [SPEC]\ndef foo():\n    return 99\n# [INFO]\n"

    # Check is_file_ready directly
    ready = is_file_ready(output_file)

    # Call run_extraction
    written, skipped = run_extraction(proj_dir, work_dir=work_dir, force=False, verbose=False)

    # Read result
    with open(output_file, 'r') as f:
        actual_content = f.read()

    # SPEC interpretation: "both [SPEC] marker lines and [INFO] marker lines"
    # -> file with 1 SPEC + 1 INFO qualifies -> should be skipped
    # is_file_ready: requires SPEC,SPEC,INFO,INFO in order -> returns False for 1+1
    # If is_file_ready is too strict -> code overwrites (written=1, skipped=0)
    # and content changes from "return 99" to "return 42"
    bug_reproduced = (pre_existing_content != actual_content and ready is False)

    if bug_reproduced:
        print(
            f'CONFIRMED - is_file_ready returned {ready} for 1+1 markers, '
            f'causing overwrite (written={written}, skipped={skipped}) '
            f'when spec says file with both SPEC+INFO markers should be skipped. '
            f'content changed from 99 to 42'
        )
    else:
        print(
            f'NOT CONFIRMED - is_file_ready={ready}, written={written}, skipped={skipped}, '
            f'content matches: {actual_content!r}'
        )

    shutil.rmtree(tmpdir, ignore_errors=True)

except Exception as e:
    print(f'ERROR: {e}')
    import traceback
    traceback.print_exc()
    sys.exit(1)

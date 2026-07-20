import sys
import os
import tempfile
import json
import shutil

# Ensure we can import the src module from the repo root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

tmpdir = None
try:
    from src.incremental_reasoner import check_last_run_existence

    # Create a temporary project directory
    tmpdir = tempfile.mkdtemp()
    fm_agent_dir = os.path.join(tmpdir, "fm_agent")
    extracted_dir = os.path.join(fm_agent_dir, "extracted_functions")
    os.makedirs(extracted_dir, exist_ok=True)

    # Condition 1: phases.json exists
    with open(os.path.join(fm_agent_dir, "phases.json"), "w") as f:
        json.dump({"phases": []}, f)

    # Condition 2 & 3: Create function files with [SPEC] and [INFO] markers
    # (needs at least 2 [SPEC] and 2 [INFO] for is_file_ready to return True)
    func_file = os.path.join(extracted_dir, "some_function.py")
    with open(func_file, "w") as f:
        f.write("# [SPEC]\n# Pre: ...\n# Post: ...\n# [SPEC]\n\n# [INFO]\n# ...\n# [INFO]\n")

    # Create a stray non-function file WITHOUT [SPEC]/[INFO] markers
    stray_file = os.path.join(extracted_dir, "README.md")
    with open(stray_file, "w") as f:
        f.write("# README\n\nSome documentation.\n")

    # Call the function
    actual = check_last_run_existence(tmpdir)
    # Per spec, only "function files" should be checked. README.md is not a function file,
    # so it should be ignored. All function files (some_function.py) are ready.
    expected = True
    passed = actual != expected  # True → bug confirmed (code returns False, spec says True)

except Exception as e:
    print(f'ERROR: {e}', flush=True)
    sys.exit(1)
finally:
    # Clean up the temp directory
    if tmpdir and os.path.isdir(tmpdir):
        shutil.rmtree(tmpdir, ignore_errors=True)

if passed:
    print(f'CONFIRMED — actual: {actual!r} | expected: {expected!r}', flush=True)
else:
    print(f'NOT CONFIRMED — actual matched expected: {actual!r}', flush=True)

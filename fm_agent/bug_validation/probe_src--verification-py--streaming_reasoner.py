"""Probe script for bug: src--verification-py--streaming_reasoner"""

import sys
import os
import tempfile
import shutil
import json
import concurrent.futures
from unittest.mock import patch, MagicMock

# The streaming_reasoner and is_file_ready live in src.verification
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))

# Simulate workspace path construction for the state files
_path_file = os.path.join(tempfile.gettempdir(), "fm_agent_state", "version.log")
os.makedirs(os.path.dirname(_path_file), exist_ok=True)
with open(_path_file, 'w') as f:
    f.write("dummy-commit-id")
toplevel_path = os.path.join(tempfile.gettempdir(), "fm_agent_state", "state.json")
with open(toplevel_path, 'w') as f:
    json.dump({"entry_func": None}, f)


def run_test():
    """Drive the bug reproduction."""
    from src.verification import streaming_reasoner

    # Create fresh temp workspace (NOT under fm_agent/)
    workspace = tempfile.mkdtemp(prefix="probe_workspace_")
    input_dir = os.path.join(workspace, "input")
    output_dir = os.path.join(workspace, "output")
    proj_dir = os.path.join(workspace, "project")
    os.makedirs(input_dir)
    os.makedirs(output_dir)
    os.makedirs(proj_dir)

    # Create a "ready" file — it has the required SPEC/SPEC/INFO/INFO markers
    ready_content = """# [SPEC]
# test spec
# [SPEC]
# [INFO]
# test info
# [INFO]
def example():
    pass
"""
    ready_path = os.path.join(input_dir, "ready_file.py")
    with open(ready_path, "w") as f:
        f.write(ready_content)

    # Create a second ready file
    ready_path2 = os.path.join(input_dir, "ready_file2.py")
    with open(ready_path2, "w") as f:
        f.write(ready_content)

    # file_list includes both files (relative paths from input_dir)
    file_list = ["ready_file.py", "ready_file2.py"]

    # spec_procs: already-finished futures so the early exit path triggers
    ex = concurrent.futures.ThreadPoolExecutor(max_workers=1)
    done_future = ex.submit(lambda: 0)
    done_future.result()  # ensure it is done

    # Strategy:
    # 1. The real is_file_ready returns True for the files (they have markers).
    # 2. But if the scan loop finds them ready, they get submitted → no bug.
    # 3. The bug is: if a file becomes ready BETWEEN the scan and the early-exit
    #    check (or spec_procs finish), the early exit fires without re-checking.
    #
    # To trigger this deterministically: make is_file_ready return False on the
    # first call (simulating "not ready yet"), then True on subsequent calls.
    # The scan loop passes over the file as "not ready". The early exit fires.
    # The next scan would have picked it up but never gets to run.

    call_counts = {}

    def controlled_is_file_ready(file_path):
        count = call_counts.get(file_path, 0)
        call_counts[file_path] = count + 1
        if count == 0:
            # First call: pretend file is NOT ready
            return False
        # Subsequent calls: file IS ready
        return True

    # Mock _verify_single_file so we don't invoke LLMs or OpenCode
    def fake_verify(file_path, input_dir_arg, output_dir_arg, language, work_dir_arg, resume_arg):
        rel = os.path.relpath(file_path, input_dir_arg)
        out_path = os.path.join(output_dir_arg, os.path.splitext(rel)[0] + ".json")
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        with open(out_path, "w") as f:
            json.dump({"function": file_path, "verdict": "MATCH", "gaps": None}, f)
        return (file_path, "MATCH")

    with patch("src.verification.is_file_ready", side_effect=controlled_is_file_ready), \
         patch("src.verification._verify_single_file", side_effect=fake_verify), \
         patch("src.verification._generate_validation_summary", return_value=None), \
         patch("src.verification.MAX_WORKERS", 2):

        result = streaming_reasoner(
            input_dir=input_dir,
            output_dir=output_dir,
            file_list=file_list,
            proj_dir=proj_dir,
            work_dir=proj_dir,
            poll_interval=0.01,
            spec_procs=[done_future],
            already_processed=None,
            resume=False,
        )

    ex.shutdown(wait=False)

    # ---------- Verdict ----------
    # Check whether all expected files are in the returned processed set.
    expected_files = {os.path.join(input_dir, rel) for rel in file_list}
    missing = expected_files - result

    if missing:
        # Bug reproduced: some expected files were never processed.
        rel_missing = [os.path.relpath(m, input_dir) for m in sorted(missing)]
        print(f"CONFIRMED — missed ready file(s): {rel_missing} | processed: {[os.path.relpath(p, input_dir) for p in sorted(result)]}")
    else:
        print(f"NOT CONFIRMED — all {len(file_list)} files processed: {[os.path.relpath(p, input_dir) for p in sorted(result)]}")

    # Cleanup
    shutil.rmtree(workspace, ignore_errors=True)


try:
    run_test()
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

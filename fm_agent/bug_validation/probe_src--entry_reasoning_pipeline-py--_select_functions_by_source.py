import sys
import os
import tempfile
import shutil

# Add project root to path so src.entry_reasoning_pipeline resolves
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# Actually, use the snapshot root
sys.path.insert(0, "/tmp/fm_agent_wt_FM-Agent_9w930mtx/snapshot")

try:
    from src.entry_reasoning_pipeline import _select_functions_by_source

    # Create a temp directory with a single valid Python source file containing one function.
    # This ensures extraction finds functions, but entry_func won't match any of them.
    tmp_dir = tempfile.mkdtemp(prefix="bug_probe_")
    src_file = os.path.join(tmp_dir, "hello.py")
    with open(src_file, "w") as f:
        f.write("def hello():\n    return 'world'\n")

    try:
        # According to the spec, this should raise ValueError because entry_func
        # is not among the extracted functions.
        _select_functions_by_source(
            tmp_dir,
            "nonexistent_module::nonexistent_func",
            end_funcs=[],
        )
        # If we reach here, no ValueError was raised — the bug is NOT confirmed.
        print("NOT CONFIRMED — no ValueError raised for missing entry_func; the check is not present")
    except ValueError as e:
        msg = str(e)
        if "entry_func" in msg and "not found" in msg:
            print(f"NOT CONFIRMED — ValueError was raised for missing entry_func, as the spec requires: {msg}")
        else:
            print(f"CONFIRMED — unexpected ValueError raised (not the entry_func check): {msg}")
    except Exception as e:
        print(f"ERROR: {type(e).__name__}: {e}")
        sys.exit(1)
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)
except Exception as e:
    print(f"ERROR during import/setup: {type(e).__name__}: {e}")
    sys.exit(1)

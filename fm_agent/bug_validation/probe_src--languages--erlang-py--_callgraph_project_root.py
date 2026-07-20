import sys
import os
import tempfile
import shutil

# Add the snapshot root to the Python path so we can import from src/
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.languages.erlang import _callgraph_project_root

bug_id = "src--languages--erlang-py--_callgraph_project_root"
probe_output = None

# Build a temporary directory structure that triggers the bug:
#   parent/
#     test/           <-- directory name in _SKIP_DIRS
#       dummy.erl     <-- only .erl file, hidden by _iter_project_files
#     workspace/
#       extracted_functions/   <-- marks this as an FM-Agent workspace
#
# proj_dir = parent/workspace
#   -> spec:  parent contains .erl, return parent
#   -> bug:   _iter_project_files skips test/, so .erl is invisible, return workspace

tmp_root = tempfile.mkdtemp(prefix="bug_probe_")

try:
    # parent directory
    parent_dir = os.path.join(tmp_root, "parent")

    # workspace with extracted_functions subdirectory
    workspace_dir = os.path.join(parent_dir, "workspace")
    extracted_func_dir = os.path.join(workspace_dir, "extracted_functions")
    os.makedirs(extracted_func_dir)

    # test/ directory (name is in _SKIP_DIRS) with a .erl file inside
    test_dir = os.path.join(parent_dir, "test")
    os.makedirs(test_dir)
    erl_file = os.path.join(test_dir, "dummy.erl")
    with open(erl_file, "w") as f:
        f.write("-module(dummy).\n-export([hello/0]).\nhello() -> ok.\n")

    # Call _callgraph_project_root with workspace_dir as proj_dir
    actual = _callgraph_project_root(workspace_dir)
    actual = os.path.realpath(actual)

    # Spec says: parent has .erl → return parent
    expected = os.path.realpath(parent_dir)

    passed = actual != expected  # True → bug reproduced (actual != expected)

    if passed:
        print(f"CONFIRMED — actual: {actual!r} | expected: {expected!r}")
        print(f"  Trigger: .erl file at {erl_file!r} inside _SKIP_DIRS directory 'test'")
        print(f"  was not found by _iter_project_files, so _callgraph_project_root")
        print(f"  returned proj_dir instead of parent.")
    else:
        print(f"NOT CONFIRMED — actual matched expected: {actual!r}")

except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

finally:
    shutil.rmtree(tmp_root, ignore_errors=True)

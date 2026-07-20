import sys
sys.path.insert(0, '/tmp/fm_agent_wt_FM-Agent_dlsr6ukl/snapshot')

import os
import tempfile
import shutil

try:
    from src.languages.codegraph import try_codegraph_init

    # Bug trigger: .codegraph/ directory exists but codegraph.db does NOT exist.
    # Spec's "Otherwise" case applies (codegraph.db missing) → requires directory removal.
    # Code at line 400 only checks os.path.exists(db_path), so it skips to the else
    # branch without removing the existing .codegraph/ directory.

    tmp = tempfile.mkdtemp()
    codegraph_dir = os.path.join(tmp, ".codegraph")
    os.makedirs(codegraph_dir)
    marker_file = os.path.join(codegraph_dir, "marker.txt")
    with open(marker_file, "w") as f:
        f.write("this marker proves the directory was not removed")

    # spec_claim: when codegraph.db doesn't exist (Otherwise case), if .codegraph/
    #   exists, it must be removed before rebuilding.
    # actual_behavior (bug): directory is NOT removed because the code only checks
    #   for db_path existence.
    try_codegraph_init(tmp, force=False)

    # If the spec was followed: marker_file should be gone (rmtree deleted .codegraph/)
    # If the bug exists: marker_file still there (dir was never removed)
    marker_exists = os.path.exists(marker_file)
    expected = False  # spec requires removal
    passed = marker_exists != expected  # True → bug reproduced

except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)
finally:
    # Cleanup temp directory
    try:
        shutil.rmtree(tmp, ignore_errors=True)
    except Exception:
        pass

if passed:
    print(f'CONFIRMED — marker file {"still exists (.codegraph/ not removed by function)" if marker_exists else "unexpectedly missing"} | spec requires removal of .codegraph/ when codegraph.db is absent')
else:
    print(f'NOT CONFIRMED — marker file was {"removed (spec correct)" if not marker_exists else "still exists but expected was confused"}')

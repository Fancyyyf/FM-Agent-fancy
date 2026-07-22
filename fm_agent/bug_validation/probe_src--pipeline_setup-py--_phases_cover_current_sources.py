import sys
import os
import json
import tempfile

try:
    import src.pipeline_setup as psetup

    # Create a temporary directory for fixtures (FM-Agent guard rule).
    tmpdir = tempfile.mkdtemp(prefix="bug_probe_")

    # proj_dir: a temp subdirectory that definitely does NOT contain /etc/hostname
    proj_dir = os.path.join(tmpdir, "fake_project")
    os.makedirs(proj_dir, exist_ok=True)

    # phases.json with an absolute path to a file outside proj_dir
    phases_json_path = os.path.join(tmpdir, "phases.json")
    phases_data = {
        "phases": [
            {
                "phase": 1,
                "modules": [
                    {
                        "module": "test",
                        "source_files": [
                            "/etc/hostname"  # absolute path outside proj_dir
                        ]
                    }
                ]
            }
        ]
    }
    with open(phases_json_path, "w") as f:
        json.dump(phases_data, f)

    # Call the function under test.
    # Spec (post-condition c): "every source file path listed in the JSON
    #   resolves to an existing file under proj_dir"
    # /etc/hostname exists but is NOT under proj_dir, so the spec requires False.
    actual = psetup._phases_cover_current_sources(phases_json_path, proj_dir)
    expected = False

    passed = actual != expected  # True means bug reproduced (actual=True, expected=False)

    if passed:
        print(
            "CONFIRMED -- actual: {!r} | expected: {!r} | "
            "absolute path /etc/hostname (exists) passed the existence check "
            "via os.path.join(proj_dir, '/etc/hostname') = '/etc/hostname', "
            "but the spec requires False because the file is not under proj_dir.".format(
                actual, expected
            )
        )
    else:
        print(
            "NOT CONFIRMED -- actual matched expected: {!r}".format(actual)
        )

    # Cleanup
    import shutil
    shutil.rmtree(tmpdir, ignore_errors=True)

except Exception as e:
    import traceback
    print("ERROR: {}".format(e))
    traceback.print_exc()
    sys.exit(1)

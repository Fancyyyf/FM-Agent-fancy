import sys
import os
import tempfile
import shutil

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + "/../..")

try:
    import config
    from src.languages.codegraph import _codegraph_cmd

    tmpdir = tempfile.mkdtemp(prefix="probe_codegraph_cmd_")
    relbin = os.path.join(tmpdir, "relbin")
    os.makedirs(relbin)
    codegraph_path = os.path.join(relbin, "codegraph")
    with open(codegraph_path, "w") as f:
        f.write("#!/bin/sh\necho ok")
    os.chmod(codegraph_path, 0o755)

    rel_bin_dir = os.path.relpath(relbin, os.getcwd())

    original_bin_dir = config.settings.codegraph.bin_dir
    config.settings.codegraph.bin_dir = rel_bin_dir

    actual = _codegraph_cmd()

    config.settings.codegraph.bin_dir = original_bin_dir

    if actual == "codegraph":
        print("NOT CONFIRMED — fallback 'codegraph' returned; executable at "
              + repr(rel_bin_dir) + " not detected")
    else:
        if os.path.isabs(actual):
            print("NOT CONFIRMED — returned absolute path: " + repr(actual))
        else:
            print("CONFIRMED — returned relative path: " + repr(actual)
                  + ", spec requires absolute")

    shutil.rmtree(tmpdir)

except Exception as e:
    import traceback
    print("ERROR: " + str(e))
    traceback.print_exc()
    sys.exit(1)

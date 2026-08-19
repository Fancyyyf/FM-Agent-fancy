import sys
import os
import tempfile

repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, repo_root)

from src.file_utils import collect_file_names

def run_probe():
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create files: sidecar suffixes should be skipped by _is_metadata_sidecar
        sidecar_spec = os.path.join(tmpdir, "a.spec.json")
        sidecar_info = os.path.join(tmpdir, "a.info.json")
        regular_py   = os.path.join(tmpdir, "a.py")
        regular_txt  = os.path.join(tmpdir, "b.txt")

        for p in (sidecar_spec, sidecar_info, regular_py, regular_txt):
            open(p, "w").close()

        result = collect_file_names(tmpdir, output_path=os.path.join(tmpdir, "output.json"))

        # spec_claim: sidecar files (ending .spec.json / .info.json) should be filtered out
        # actual_behavior: _is_metadata_sidecar uses str.endswith(tuple) which works correctly
        expected = sorted(["a.py", "b.txt"])

        if result == expected:
            print("NOT CONFIRMED — _is_metadata_sidecar correctly returns boolean. "
                  "_METADATA_SIDECAR_SUFFIXES is a tuple, str.endswith(tuple) works in Python. "
                  "No TypeError occurs. The function satisfies its specification.")
        else:
            print(f"CONFIRMED — result: {result!r}, expected: {expected!r}")

try:
    run_probe()
except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)

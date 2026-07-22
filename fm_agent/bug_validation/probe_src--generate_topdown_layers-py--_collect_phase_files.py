import sys
import os
import tempfile

# Add repo root to path so `src` is importable
_repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, _repo_root)

try:
    from src.generate_topdown_layers import _collect_phase_files
except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)

# Create temp workspace — all fixtures isolated from the repo
tmpdir = tempfile.mkdtemp(prefix="probe_collect_phase_files_")
extracted_base = os.path.join(tmpdir, "extracted_functions")

# Directory the spec says should be looked up: -hidden
# (basename ".hidden" → replace last "." with "-" → "-hidden")
spec_correct_dir = os.path.join(extracted_base, "-hidden")
os.makedirs(spec_correct_dir, exist_ok=True)
with open(os.path.join(spec_correct_dir, "correct_file.py"), "w") as f:
    f.write("# spec correct\n")

# Directory the buggy code actually looks up: .hidden
# (last_dot == 0, last_dot > 0 is False, dir_name stays ".hidden")
buggy_dir = os.path.join(extracted_base, ".hidden")
os.makedirs(buggy_dir, exist_ok=True)
with open(os.path.join(buggy_dir, "buggy_file.py"), "w") as f:
    f.write("# buggy\n")

# phase_data with a source file whose basename starts with a "." (dot file)
phase_data = {
    "modules": [
        {
            "name": "test_module",
            "source_files": [".hidden"]
        }
    ]
}

results = _collect_phase_files(tmpdir, phase_data)
actual_files = {os.path.normpath(fp) for fp, _ in results}

spec_expected = {os.path.normpath(os.path.join(spec_correct_dir, "correct_file.py"))}
buggy_expected = {os.path.normpath(os.path.join(buggy_dir, "buggy_file.py"))}

# Cleanup before reporting
import shutil
shutil.rmtree(tmpdir, ignore_errors=True)

if actual_files == spec_expected:
    print(f'NOT CONFIRMED — actual matched spec-expected: {actual_files}')
elif actual_files == buggy_expected:
    print(f'CONFIRMED — actual: {actual_files} | spec-expected (look in -hidden/): {spec_expected} | code looked in .hidden/ instead because last_dot>0 is False when last_dot==0')
elif not actual_files:
    print(f'NOT CONFIRMED — no files found (maybe neither directory was checked or dirs were cleaned)')
else:
    print(f'ERROR: unexpected result: actual={actual_files}, spec_expected={spec_expected}, buggy_expected={buggy_expected}')

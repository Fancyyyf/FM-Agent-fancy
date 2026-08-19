"""Probe script for bug src--file_utils-py--_get_incomplete_verification_files.

The spec requires bug_id to be derived from the relative path by replacing
every '/' and os.sep with '--' without removing the file extension. The code
(line 153) uses os.path.splitext to strip the extension first, causing a
mismatch between the spec's expected bug validation file path and the code's
actual lookup.
"""
import sys
import os
import json
import tempfile
from pathlib import Path

_repo_root = Path(__file__).resolve().parent.parent.parent
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))

try:
    from src.file_utils import _get_incomplete_verification_files
except Exception as exc:
    print(f'ERROR: could not import: {exc}')
    sys.exit(1)

probe_tmp = tempfile.mkdtemp(prefix="probe_")
print(f"Probe workspace: {probe_tmp}", file=sys.stderr)

output_dir = os.path.join(probe_tmp, "output")
work_dir = os.path.join(probe_tmp, "work")
os.makedirs(output_dir)
os.makedirs(os.path.join(work_dir, "bug_validation"))

# Use a rel path with an extension to trigger the splitext mismatch.
rel = "foo/bar.py"

# 1. Create a verification result file with verdict "MISMATCH" for this rel.
result_path = os.path.join(output_dir, os.path.splitext(rel)[0] + ".json")
os.makedirs(os.path.dirname(result_path), exist_ok=True)
with open(result_path, "w") as f:
    json.dump({"verdict": "MISMATCH"}, f)

# 2. Create a valid bug validation result file at the SPEC-expected path
#    (where '/' is replaced with '--' WITHOUT stripping the .py extension).
spec_bug_id = rel.replace(os.sep, "--").replace("/", "--")  # "foo--bar.py"
spec_validation_path = os.path.join(
    work_dir, "bug_validation", f"{spec_bug_id}.result.json"
)
os.makedirs(os.path.dirname(spec_validation_path), exist_ok=True)
with open(spec_validation_path, "w") as f:
    json.dump({"confirmation_status": "confirmed"}, f)

# 3. Do NOT create a bug validation result at the CODE-expected path.
#    The code uses splitext, so it looks for "foo--bar.result.json" which
#    does not exist.

# 4. Call the function under test.
try:
    incomplete = _get_incomplete_verification_files(
        [rel], "dummy_input_dir", output_dir, work_dir
    )
except Exception as exc:
    print(f'ERROR: _get_incomplete_verification_files raised: {exc}')
    sys.exit(1)

# 5. Check result.
# The spec says: since the validation file exists at the spec path,
# the entry is complete and should NOT be in incomplete.
# The code (buggy) looks at the wrong path (missing), so it WILL incorrectly
# include the entry.
expected = []   # spec-correct: file is complete, not in incomplete list

if rel in incomplete:
    # Bug reproduced: code incorrectly included the entry.
    actual = incomplete
    print(
        f"CONFIRMED — actual: {actual!r} | expected: {expected!r} | "
        f"spec_validation_path exists: {os.path.isfile(spec_validation_path)}"
    )
else:
    # Bug not reproduced: code correctly excluded the entry.
    actual = incomplete
    print(f"NOT CONFIRMED — actual matched expected: {actual!r}")

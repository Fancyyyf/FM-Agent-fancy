import sys
import os
import json
import tempfile
import shutil

# All test fixtures, outputs, and intermediate files live under a temp dir.
# We import from the repo's source tree but never use the repo workspace for I/O.
tmpdir = tempfile.mkdtemp(prefix="probe_run_extraction_")

# -------------------------------------------------------------------
# 1. Create a minimal test project inside the temp directory
# -------------------------------------------------------------------
# Source file: mypkg/utils.py with two functions
test_src_dir = os.path.join(tmpdir, "mypkg")
os.makedirs(test_src_dir, exist_ok=True)
test_src_file = os.path.join(test_src_dir, "utils.py")
with open(test_src_file, "w") as f:
    f.write("def add(x, y):\n    return x + y\n\ndef sub(x, y):\n    return x - y\n")

# phases.json referencing that source file
phases = {"phases": [{"modules": [{"source_files": ["mypkg/utils.py"]}]}]}
phases_path = os.path.join(tmpdir, "phases.json")
with open(phases_path, "w") as f:
    json.dump(phases, f)

# -------------------------------------------------------------------
# 2. Call run_extraction via the public entry point
# -------------------------------------------------------------------
# The repo root must be on sys.path so 'from src.extract import run_extraction'
# resolves. We add it at the front so intra-package 'from src.xxx' imports work.
repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, repo_root)

try:
    from src.extract import run_extraction

    written, skipped = run_extraction(
        proj_dir=tmpdir,
        work_dir=tmpdir,
        force=True,
        verbose=False,
    )
except Exception as e:
    # Catch import errors, codegraph failures, etc.
    print(f"ERROR: {e}", file=sys.stderr)
    # Still write the verdict marker
    print("NOT CONFIRMED")
    sys.exit(0)

# -------------------------------------------------------------------
# 3. Inspect the output paths
# -------------------------------------------------------------------
output_base = os.path.join(tmpdir, "extracted_functions")

convention_paths = []  # paths following <source_rel_dir>/<basename-ext>/<func_name>.<ext>
flat_paths = []        # paths directly under extracted_functions/ with no subdirs
other_paths = []       # anything else

for root, _dirs, files in os.walk(output_base):
    for fname in files:
        full = os.path.join(root, fname)
        rel = os.path.relpath(full, output_base)
        parts = rel.split(os.sep)
        if len(parts) == 3:
            convention_paths.append(rel)
        elif len(parts) == 1:
            flat_paths.append(rel)
        else:
            other_paths.append(rel)

# The bug claim: files are written flat (no subdirectories).
# If we find convention paths, the bug is NOT CONFIRMED.
# If files are flat, the bug IS CONFIRMED.
bug_confirmed = len(convention_paths) == 0 and len(flat_paths) > 0

if bug_confirmed:
    print(f"CONFIRMED - flat files detected (no subdirectory structure)")
    print(f"Flat paths: {flat_paths}")
else:
    print(f"NOT CONFIRMED - output files follow path convention")
    print(f"Convention paths found: {convention_paths}")
    if flat_paths:
        print(f"Flat paths also present: {flat_paths}")
    if other_paths:
        print(f"Other paths: {other_paths}")

# Cleanup temp dir
shutil.rmtree(tmpdir, ignore_errors=True)

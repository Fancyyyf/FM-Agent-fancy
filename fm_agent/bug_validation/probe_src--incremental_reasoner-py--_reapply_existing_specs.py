"""Probe script for bug: _reapply_existing_specs returns None instead of count."""
import os
import sys
import tempfile
import shutil

# Add repo root to sys.path for imports
# Probe is at: snapshot/fm_agent/bug_validation/probe_*.py
# Go up 3 levels to reach snapshot (repo root)
repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, repo_root)

try:
    from src.incremental_reasoner import _reapply_existing_specs
except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)

# Create a temporary project directory structure to test against
proj_dir = tempfile.mkdtemp(prefix="probe_reapply_")
extracted_dir = os.path.join(proj_dir, "fm_agent", "extracted_functions")
os.makedirs(extracted_dir, exist_ok=True)

# Create test files
# file_a: exists, no [SPEC] header → should be modified
file_a_path = os.path.join(extracted_dir, "file_a.py")
with open(file_a_path, "w") as f:
    f.write("def foo():\n    return 42\n")

# file_b: exists, no [SPEC] header → should be modified
file_b_path = os.path.join(extracted_dir, "file_b.py")
with open(file_b_path, "w") as f:
    f.write("def bar():\n    return 'hello'\n")

# file_c: exists, HAS [SPEC] in first line → should be SKIPPED (idempotent)
file_c_path = os.path.join(extracted_dir, "file_c.py")
with open(file_c_path, "w") as f:
    f.write("# [SPEC]\n# pre-existing header\n# [SPEC]\ndef baz():\n    pass\n")

# file_d: does NOT exist as a file → directory to test missing path
os.makedirs(os.path.join(extracted_dir, "file_d.py"), exist_ok=True)

# Build the specs dict matching what extract_existing_specs would return
specs = {
    "file_a.py": {"spec": "# [SPEC]\n# spec for file_a\n# [SPEC]"},
    "file_b.py": {"spec": "# [SPEC]\n# spec for file_b\n# [SPEC]", "info": "# [INFO]\n# info for file_b\n# [INFO]"},
    "file_c.py": {"spec": "# [SPEC]\n# new spec for file_c (should NOT be applied)\n# [SPEC]"},
    "file_d.py": {"spec": "# [SPEC]\n# spec for file_d (should be skipped, no file)\n# [SPEC]"},
    "file_e.py": {"spec": ""},  # falsy spec → skip
}

actual = None
passed = False

try:
    actual = _reapply_existing_specs(proj_dir, specs)
    # The spec says it should return the count of modified files (2: file_a, file_b).
    # The bug is that it returns None instead.
    expected = 2
    passed = actual != expected  # True → bug reproduced (returned None, not 2)
except Exception as e:
    print(f'ERROR: {e}')
    shutil.rmtree(proj_dir, ignore_errors=True)
    sys.exit(1)

# Cleanup
shutil.rmtree(proj_dir, ignore_errors=True)

if passed:
    print(f'CONFIRMED — actual: {actual!r} | expected: {expected!r}')
else:
    print(f'NOT CONFIRMED — actual matched expected: {actual!r}')

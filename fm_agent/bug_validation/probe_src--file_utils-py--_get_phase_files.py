"""Probe script for _get_phase_files bug: os.walk order vs spec-required sort order."""
import sys
import os
import json
import tempfile

# ---------- create a reproducible trigger scenario ----------
#
# The spec says: "Within each extracted-function subdirectory, contained
# regular files appear in lexicographically sorted order by filename."
# When a subdirectory exists under the extracted-function directory, os.walk
# visits files in the parent before files in the child (top-down).  This
# violates the global-sort requirement.
#
# Trigger: create an extracted-dir that contains both a root-level file
# ("z.txt") and a child-directory file ("sub/a.txt").  The spec demands
# [".../sub/a.txt", ".../z.txt"] (alphabetical by filename), but os.walk
# returns [".../z.txt", ".../sub/a.txt"].
# ----------------------------------------------------------------

# Project root – needed so that `import src` resolves this project
PROJ_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, PROJ_ROOT)

try:
    from src.file_utils import _get_phase_files
except ImportError as e:
    print(f"ERROR: cannot import _get_phase_files: {e}")
    sys.exit(1)

# Build the fixture inside a fresh temporary directory (self-contained).
tmp_dir = tempfile.mkdtemp(prefix="probe_get_phase_files_")

try:
    input_dir = os.path.join(tmp_dir, "input_dir")
    os.makedirs(input_dir)

    # extracted-function subdirectory: src/file-cpp (file.cpp → file-cpp convention)
    extract_subdir = os.path.join(input_dir, "src", "file-cpp")
    child_dir = os.path.join(extract_subdir, "sub")
    os.makedirs(child_dir)

    # Root-level file inside extracted_dir (lexicographically "z.txt" > "a.txt")
    root_z = os.path.join(extract_subdir, "z.txt")
    with open(root_z, "w") as f:
        f.write("z")

    # Nested file inside sub/ (lexicographically "a.txt" < "z.txt")
    child_a = os.path.join(child_dir, "a.txt")
    with open(child_a, "w") as f:
        f.write("a")

    phases_data = {
        "phases": [
            {
                "phase": 1,
                "modules": [
                    {
                        "source_files": ["src/file.cpp"]
                    }
                ]
            }
        ]
    }

    actual = _get_phase_files(phases_data, 1, input_dir)

    # Expected (spec-correct): all regular files sorted by filename globally
    expected = sorted(actual, key=lambda p: os.path.basename(p))

    passed = actual != expected  # True → bug reproduced

    if passed:
        print(
            f"CONFIRMED — actual (os.walk order): {actual!r} | "
            f"expected (spec order): {expected!r}"
        )
    else:
        print(f"NOT CONFIRMED — actual matched expected: {actual!r}")

finally:
    # Clean up the temporary fixture
    import shutil
    shutil.rmtree(tmp_dir, ignore_errors=True)

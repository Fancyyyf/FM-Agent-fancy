"""
Probe script for bug ID: src--incremental_reasoner-py--_collect_changed_functions

Tests whether _collect_changed_functions correctly filters files by the
submodules parameter. Creates a temporary git repository with source files
inside and outside a submodule directory, then verifies that only files
within the specified submodule scope appear in the result.
"""

import os
import sys
import subprocess
import tempfile
import shutil

# ---------------------------------------------------------------------------
# Step 1 — Create a temporary git repo with test files
# ---------------------------------------------------------------------------
tmpdir = tempfile.mkdtemp(prefix="probe_collect_changed_")

def _git(cwd, *args):
    return subprocess.run(
        ["git", "-C", cwd, *args],
        check=True, capture_output=True, text=True,
    ).stdout.strip()

try:
    # git init + configure user (required for commits)
    _git(tmpdir, "init")
    _git(tmpdir, "config", "user.email", "probe@fm-agent.test")
    _git(tmpdir, "config", "user.name", "FM-Agent Probe")

    # Create a source file INSIDE the submodule "mylib"
    lib_dir = os.path.join(tmpdir, "mylib")
    os.makedirs(lib_dir, exist_ok=True)
    lib_file = os.path.join(lib_dir, "utils.py")
    with open(lib_file, "w") as f:
        f.write('def greet(name):\n    return f"Hello, {name}"\n')

    # Create a source file OUTSIDE the submodule (in the repo root)
    top_file = os.path.join(tmpdir, "main.py")
    with open(top_file, "w") as f:
        f.write('def run():\n    print("running")\n')

    _git(tmpdir, "add", "mylib/utils.py", "main.py")
    _git(tmpdir, "commit", "-m", "initial commit")

    # Get the commit hash to use as old_commit_id
    old_commit = _git(tmpdir, "rev-parse", "HEAD")

    # Modify BOTH files so they show as changed
    with open(lib_file, "w") as f:
        f.write('def greet(name):\n    return f"Hi, {name}!"\n')

    with open(top_file, "w") as f:
        f.write('def run():\n    print("launching")\n')

    # ---------------------------------------------------------------------------
    # Step 2 — Import _collect_changed_functions from the package
    # ---------------------------------------------------------------------------
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                     "..", ".."))
    from src.incremental_reasoner import _collect_changed_functions

    # ---------------------------------------------------------------------------
    # Step 3 — Call with submodules=['mylib']
    # ---------------------------------------------------------------------------
    result_scoped = _collect_changed_functions(tmpdir, old_commit, submodules=["mylib"])
    rel_scoped = set(
        os.path.relpath(p, tmpdir).replace("\\", "/")
        for p in result_scoped
    )

    # ---------------------------------------------------------------------------
    # Step 4 — Call without submodules (None)
    # ---------------------------------------------------------------------------
    result_full = _collect_changed_functions(tmpdir, old_commit, submodules=None)
    rel_full = set(
        os.path.relpath(p, tmpdir).replace("\\", "/")
        for p in result_full
    )

    # ---------------------------------------------------------------------------
    # Step 5 — Verify the results
    # ---------------------------------------------------------------------------
    # The spec claims: when submodules is provided, files outside the given
    # submodule directories must be excluded.
    # Bug condition: submodule-scoped result includes a file OUTSIDE the scope.

    outside_file_present = any(
        "main.py" in rel for rel in rel_scoped
    )
    inside_file_present = any(
        "mylib/utils.py" in rel for rel in rel_scoped
    )
    full_has_both = "mylib/utils.py" in rel_full and "main.py" in rel_full

    # Print diagnostics
    print(f"scoped (submodules=['mylib']): {sorted(rel_scoped)}")
    print(f"full    (submodules=None):      {sorted(rel_full)}")
    print(f"inside file in scoped: {inside_file_present}")
    print(f"outside file in scoped: {outside_file_present}")
    print(f"full has both: {full_has_both}")

    # Bug is confirmed IF: the outside file appears in the scoped result,
    # meaning submodule filtering did NOT work.
    if outside_file_present:
        print(
            "CONFIRMED — submodule filtering failed: "
            f"main.py appeared in scoped result despite submodules=['mylib']"
        )
    elif inside_file_present and full_has_both:
        print(
            "NOT CONFIRMED — submodule filtering works correctly: "
            "main.py excluded from scoped result, both files in full result"
        )
    else:
        print(
            "NOT CONFIRMED — unexpected result state: "
            f"inside={inside_file_present}, outside={outside_file_present}, "
            f"full_both={full_has_both}"
        )

except subprocess.CalledProcessError as e:
    print(f"ERROR: git command failed: {e}")
    sys.exit(1)
except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)
finally:
    # Clean up the temporary git repo
    shutil.rmtree(tmpdir, ignore_errors=True)

"""Probe script for bug: _phases_cover_current_sources accepts empty-string source_file paths.

Bug ID: src--pipeline_setup-py--_phases_cover_current_sources

The specification requires every listed source file path to be a normalized
forward-slash path. The code only replaces backslashes with forward slashes and
does not reject non-normalized paths like empty strings, allowing an empty string
to pass the existence check (os.path.join(proj_dir, "") == proj_dir, which exists).

This probe creates a temporary directory with a valid .py source file, writes a
phases.json that includes both the valid file AND an empty string source_file, then
calls _phases_cover_current_sources to check whether the function incorrectly
returns True despite the non-normalized empty-string path.
"""

import json
import os
import sys
import tempfile

# Add repo root to path so 'config' and 'src' are importable
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _REPO_ROOT)

try:
    from src.pipeline_setup import _phases_cover_current_sources
except ImportError as e:
    print(f"ERROR: Could not import _phases_cover_current_sources: {e}")
    sys.exit(1)


def run_probe():
    """Create temp fixtures and test the bug."""
    tmpdir = tempfile.mkdtemp(prefix="bug_validator_probe_")

    try:
        # 1. Create a dummy .py source file so _collect_project_source_files
        #    discovers it via _iter_project_source_files (which filters by
        #    EXT_TO_LANG from src.extract).
        dummy_py = os.path.join(tmpdir, "dummy.py")
        with open(dummy_py, "w") as f:
            f.write("# dummy source file for bug probe\n")

        # 2. Create phases.json that lists:
        #    - the valid source file "dummy.py"
        #    - an empty string "" as a non-normalized path
        phases_path = os.path.join(tmpdir, "phases.json")
        phases_data = {
            "phases": [
                {
                    "phase": 1,
                    "name": "Test Phase",
                    "description": "Probe phase",
                    "modules": [
                        {
                            "name": "test_module",
                            "description": "Probe module with buggy empty-string source_file",
                            "source_files": ["dummy.py", ""]
                        }
                    ],
                    "depends_on_phases": []
                }
            ]
        }
        with open(phases_path, "w") as f:
            json.dump(phases_data, f, indent=2)

        # 3. Call _phases_cover_current_sources
        #    Spec says: returns False because "" is not a normalized path
        #    Code bug:  returns True because "" passes all checks
        actual = _phases_cover_current_sources(phases_path, tmpdir)

        # 4. Determine expected (spec-correct) value
        #    Per spec condition (2): "every source file path listed under
        #    'phases' is a normalized forward-slash path that corresponds to
        #    an existing file relative to proj_dir"
        #    An empty string is NOT a normalized forward-slash path.
        expected = False

        # Bug is CONFIRMED if actual != expected (code behaves against spec)
        passed = actual != expected

    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)
    finally:
        # Clean up temp directory
        import shutil
        shutil.rmtree(tmpdir, ignore_errors=True)

    if passed:
        print(f"CONFIRMED — actual: {actual!r} | expected: {expected!r}")
    else:
        print(f"NOT CONFIRMED — actual matched expected: {actual!r}")


if __name__ == "__main__":
    run_probe()

"""Probe for bug src--extract-py--run_extraction (attempt 3).

Maximal counterexample: phases.json now lists one entry of each category the
specification declares uncountable —
  1. "tests/test_foo.py"  (exists on disk, detected as a test file)
  2. "src/missing.py"     (listed but absent on disk)
  3. "data/notes.xyz"     (exists on disk, extension maps to no language)

The verification result's actual_behavior claim counts every unprocessed
source-file entry into skipped_count, i.e. expected buggy output (0, 3). The
specification requires that test files, missing files, and files with unmapped
extensions contribute neither to the written nor the skipped count, i.e.
spec-correct output (0, 0).

FM-Agent self-validation guard: no FM-Agent workflow is started; the probe
exercises the smallest relevant unit, src.extract.run_extraction, against a
throwaway fixture project in a fresh temporary directory.
"""

import json
import os
import sys
import tempfile

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)


def main():
    from src.extract import run_extraction

    proj_dir = tempfile.mkdtemp(prefix="fm_probe_run_extraction_")

    os.makedirs(os.path.join(proj_dir, "tests"))
    os.makedirs(os.path.join(proj_dir, "data"))
    with open(os.path.join(proj_dir, "tests", "test_foo.py"), "w", encoding="utf-8") as f:
        f.write("def helper():\n    return 1\n")
    with open(os.path.join(proj_dir, "data", "notes.xyz"), "w", encoding="utf-8") as f:
        f.write("no language maps to .xyz\n")
    # src/missing.py deliberately not created.

    phases = {"phases": [{"modules": [{"source_files": [
        "tests/test_foo.py",
        "src/missing.py",
        "data/notes.xyz",
    ]}]}]}
    with open(os.path.join(proj_dir, "phases.json"), "w", encoding="utf-8") as f:
        json.dump(phases, f)

    actual = run_extraction(proj_dir)

    # Spec-correct: none of the three categories counts -> (0, 0).
    # Claimed buggy behavior: each unprocessed entry counted -> (0, 3).
    expected = (0, 0)
    passed = actual != expected  # True -> bug reproduced

    if passed:
        print(f"CONFIRMED — actual: {actual!r} | expected: {expected!r}")
    else:
        print(f"NOT CONFIRMED — actual matched expected: {actual!r}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"ERROR: {type(e).__name__}: {e}")
        sys.exit(1)

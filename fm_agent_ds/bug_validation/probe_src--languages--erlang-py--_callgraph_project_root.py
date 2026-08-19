"""Probe for bug: _callgraph_project_root uses _SKIP_DIRS-filtered _iter_project_files
to check for .erl files, violating the spec which requires checking for ANY .erl file
in the parent directory without exclusions.
"""

import os
import sys
import tempfile

try:
    from src.languages.erlang import _callgraph_project_root
except ImportError:
    print("ERROR: Could not import _callgraph_project_root from src.languages.erlang")
    sys.exit(1)


def run_probe():
    """Create a temp directory structure where all .erl files in the parent
    reside in _SKIP_DIRS-excluded directories. The spec says the function should
    return parent; the buggy code returns root.
    """
    tmp = tempfile.mkdtemp(prefix="probe_callgraph_root_")

    # Structure:
    #   <tmp>/
    #     project/
    #       extracted_functions/   # triggers the parent-scan branch
    #       tests/                 # excluded by _SKIP_DIRS
    #         test.erl             # .erl file (only .erl in the tree)

    project_dir = os.path.join(tmp, "erlang_project")
    extracted_functions = os.path.join(project_dir, "extracted_functions")
    tests_dir = os.path.join(project_dir, "tests")

    os.makedirs(extracted_functions, exist_ok=True)
    os.makedirs(tests_dir, exist_ok=True)

    # Create an .erl file inside the excluded tests/ directory
    erl_path = os.path.join(tests_dir, "test.erl")
    with open(erl_path, "w") as f:
        f.write("-module(test).\n-export([hello/0]).\nhello() -> ok.\n")

    expected = tmp  # spec says: parent directory should be returned
    try:
        actual = _callgraph_project_root(project_dir)
    except Exception as e:
        print(f"ERROR: {e}")
        # Clean up
        os.unlink(erl_path)
        for d in (tests_dir, extracted_functions, project_dir, tmp):
            try:
                os.rmdir(d)
            except OSError:
                pass
        sys.exit(1)

    projected_root = os.path.abspath(project_dir)

    # Spec: parent contains .erl → return parent (tmp)
    # Buggy code: skips tests/ dir → finds no .erl → returns root (project_dir)
    spec_correct = expected
    code_result = actual

    bug_reproduced = code_result != spec_correct

    # Clean up temp files
    try:
        os.unlink(erl_path)
        for d in (tests_dir, extracted_functions, project_dir, tmp):
            try:
                os.rmdir(d)
            except OSError:
                pass
    except OSError:
        pass

    if bug_reproduced:
        print(f"CONFIRMED — actual: {actual!r} | expected: {expected!r}")
    else:
        print(
            f"NOT CONFIRMED — actual matched expected: {actual!r}"
        )


if __name__ == "__main__":
    run_probe()

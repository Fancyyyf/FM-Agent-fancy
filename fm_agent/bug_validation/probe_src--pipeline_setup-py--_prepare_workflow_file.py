import sys
import os
import tempfile
import shutil

try:
    from src.pipeline_setup import _prepare_workflow_file

    # Create a temporary script_dir with a md/ subdirectory containing
    # a workflow file that uses a REGULAR HYPHEN (-) instead of em-dash (—).
    # The code's "old" string uses an em-dash, so .replace(old, new, 1) will
    # silently fail to match, violating the spec that requires the rewrite.
    tmpdir = tempfile.mkdtemp()
    md_dir = os.path.join(tmpdir, "md")
    os.makedirs(md_dir)

    # The source file with a regular hyphen (-) instead of an em-dash (—).
    # Note: this is identical to what the spec expects, but uses - not —.
    workflow_content = (
        "- `phases[*].modules[*].source_files` - relative paths from repo root of all source files "
        "that belong to this module. **Exclude all test files** (e.g., files in `test/`, "
        "`tests/`, `__tests__/` directories, or files named `*_test.*`, `test_*.*`, `*_spec.*`)\n"
    )

    workflow_filename = "workflow_test_probe.md"
    src_path = os.path.join(md_dir, workflow_filename)
    with open(src_path, "w") as f:
        f.write(workflow_content)

    # Create separate work_dir for the output
    work_dir = tempfile.mkdtemp()
    proj_dir = tmpdir  # use tmpdir as proj_dir for testing

    # Call the function under test
    result = _prepare_workflow_file(
        proj_dir=proj_dir,
        work_dir=work_dir,
        script_dir=tmpdir,
        workflow_filename=workflow_filename,
    )

    # Read the copied file to check if the replacement happened
    dst_path = os.path.join(work_dir, workflow_filename)
    with open(dst_path, "r") as f:
        copied_content = f.read()

    # The spec says the instruction must be rewritten to reference the
    # absolute path. If the old em-dash string didn't match (because the
    # source uses a regular hyphen), the instruction will still contain
    # "repo root" — the original text — instead of the project root path.
    if "repo root" in copied_content:
        # The replacement FAILED: the old text is still present.
        # This confirms the bug: the hard-coded em-dash prevents matching
        # a workflow file that uses a regular hyphen.
        passed = True
        print(
            "CONFIRMED — replacement failed: instruction still contains "
            "'repo root' instead of project root. Source used hyphen '-', "
            "code matches only em-dash '—'."
        )
    elif "project root" in copied_content:
        # The replacement SUCCEEDED (unexpected — would mean the code is
        # more flexible than claimed).
        passed = False
        # Build what we expected
        expected = (
            f"- `phases[*].modules[*].source_files` — relative paths from the project root "
            f"`{os.path.abspath(proj_dir)}` of all source files that belong to this module. "
            f"For example, a file at `{os.path.abspath(proj_dir)}/path/to/file.ext` must be "
            f"recorded as `path/to/file.ext`, NOT as `{os.path.basename(os.path.abspath(proj_dir))}"
            f"/path/to/file.ext`."
        )
        print(
            f"NOT CONFIRMED — replacement unexpectedly matched. "
            f"Copied content:\n{copied_content[:500]}"
        )
    else:
        # Unexpected — neither keyword found
        passed = False
        print(f"NOT CONFIRMED — unexpected output. Content:\n{copied_content[:500]}")

except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

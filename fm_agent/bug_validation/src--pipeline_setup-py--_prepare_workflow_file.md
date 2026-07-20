# Bug Report: _prepare_workflow_file

**Source file:** `src/pipeline_setup-py/_prepare_workflow_file.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- A copy of the file script_dir/md/workflow_filename exists at
    work_dir/workflow_filename with file metadata preserved from the source
  - The source_files instruction in the copied file is rewritten to reference
    the absolute path of proj_dir as the project root and to include an example
    clarifying that paths must be relative to that root (not prefixed with the
    project directory name)
  - When one or more domain knowledge files are staged under work_dir, the copied
    file includes an appended section listing each staged file as a user-provided
    domain knowledge reference formatted as Markdown bullets
  - When no domain knowledge files are staged, the copied file contains only the
    rewritten source_files instruction and is otherwise identical to the source
  - The source file at script_dir/md/workflow_filename is never modified
  - Returns None on completion

---

### Actual Behavior

If the function returns normally, the file at `os.path.join(work_dir, workflow_filename)` exists and its content is equivalent to the following sequence of transformations applied to the original content of `os.path.join(script_dir, 'md', workflow_filename)`: (1) The first occurrence of the exact string `"- `phases[*].modules[*].source_files`  relative paths from repo root of all source files that belong to this module."` is replaced by `f"- `phases[*].modules[*].source_files`  relative paths from the project root `{os.path.abspath(proj_dir)}` of all source files that belong to this module. For example, a file at `{os.path.abspath(proj_dir)}/path/to/file.ext` must be recorded as `path/to/file.ext`, NOT as `{os.path.basename(os.path.abspath(proj_dir))}/path/to/file.ext`."`. (2) If `list_staged_domain_knowledge_relpaths(work_dir)` returns a non-empty list `L`, then the following multiline string is appended: `"\n---\n\n## User-Provided Domain Knowledge\n\nThe user supplied extra Markdown files with domain knowledge for this run. Read these files before writing `phases.json` and the generated domain context files. Use them only as contextual knowledge about intended behavior, terminology, business rules, data encodings, and invariants; do NOT include these Markdown files as project source files in `phases.json`, and do NOT edit or summarize them in place.\n\n" + format_domain_knowledge_bullets(L) + "\n"`. No other modifications are performed. If an exception is raised during execution, the file may be left in an intermediate state (e.g., a copy of the source file) but the function does not complete normally.

---

## Code Evidence

Line 14: old = ("- `phases[*].modules[*].source_files`  relative paths from repo root of all source files "
Line 15:        "that belong to this module.")
Line 20: md = md.replace(old, new, 1)

---

## Trigger Condition

The specification requires that the source_files instruction in the copied file be rewritten to reference the project root. The code attempts to do this by performing an exact string match and replace on a hard-coded old string that uses an em-dash (''). However, if the source file contains the instruction with a different dash (for example, a regular hyphen '-'), the replace does not match and the instruction remains unchanged. This means that for such a valid input (where the instruction is present but formatted with a standard hyphen), the code's behavior violates the specification.

---

## How to trigger the bug

The code performs `md.replace(old, new, 1)` where `old` contains a hard-coded em-dash character (`—`, U+2014). If the source workflow file (e.g., `md/workflow_generate_phases.md`) uses a regular ASCII hyphen (`-`, U+002D) instead of an em-dash in the `source_files` instruction, the string replacement silently fails. The copied workflow file then retains the original text referencing "repo root" instead of being rewritten to reference the concrete project root path.

### Inputs

| Parameter | Value |
|-----------|-------|
| proj_dir | `/tmp/test_probe_dir` (any existing directory) |
| work_dir | `/tmp/test_work_dir` (any writable directory) |
| script_dir | path containing `md/workflow_test_probe.md` |
| workflow_filename | `workflow_test_probe.md` (a file whose `source_files` instruction uses a regular hyphen `-` instead of em-dash `—`) |

### Expected (spec-correct) Output

The copied file at `work_dir/workflow_filename` should have its `source_files` instruction rewritten to reference the absolute project root path, regardless of whether the source file used an em-dash or a regular hyphen.

### Actual (buggy) Output

The copied file at `work_dir/workflow_filename` still contains the original text: `- \`phases[*].modules[*].source_files\` - relative paths from repo root...` — the replacement did not occur because the hard-coded `old` string uses an em-dash that does not match the source file's regular hyphen.

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import tempfile, os, shutil
from src.pipeline_setup import _prepare_workflow_file

tmpdir = tempfile.mkdtemp()
md_dir = os.path.join(tmpdir, "md")
os.makedirs(md_dir)

# Write a workflow file that uses a regular hyphen (-) instead of em-dash (—)
with open(os.path.join(md_dir, "test.md"), "w") as f:
    f.write('- `phases[*].modules[*].source_files` - relative paths from repo root of all source files that belong to this module.\n')

work_dir = tempfile.mkdtemp()
_prepare_workflow_file(proj_dir=tmpdir, work_dir=work_dir, script_dir=tmpdir, workflow_filename="test.md")

# Check — the copied file still says "repo root" (replacement failed)
with open(os.path.join(work_dir, "test.md")) as f:
    content = f.read()
print("repo root" in content)   # True — bug: replacement never happened
print("project root" in content) # False — spec requires this to be True
# actual (buggy) output: file unchanged, "repo root" still present
# expected (correct) output: file rewritten to use absolute project root path
```

---

## Probe Script

```python
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
```

### Probe Output

```
CONFIRMED — replacement failed: instruction still contains 'repo root' instead of project root. Source used hyphen '-', code matches only em-dash '—'.
```

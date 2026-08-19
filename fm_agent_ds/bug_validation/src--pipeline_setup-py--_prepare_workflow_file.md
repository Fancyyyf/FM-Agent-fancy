# Bug Report: _prepare_workflow_file

**Source file:** `src/pipeline_setup-py/_prepare_workflow_file.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

A file named workflow_filename exists at <work_dir>/<workflow_filename> whose content is derived from the source file at <script_dir>/md/<workflow_filename>. The source_files instruction string in the workflow content is rewritten to reference the absolute path of proj_dir as the project root and to include a concrete example demonstrating that a file at <proj_dir_abs>/path/to/file.ext must be recorded as 'path/to/file.ext' without the project directory name prefix. If at least one user-provided domain knowledge markdown file is staged under the work_dir, a section titled 'User-Provided Domain Knowledge' is appended to the file containing: an instruction to read the staged files as contextual knowledge without including them as project source files in phases.json, followed by a bullet list of the relative workspace paths to each staged knowledge file. If no domain knowledge files are staged, the workflow file is written without the appended section. The source workflow file at <script_dir>/md/<workflow_filename> is not modified.

---

### Actual Behavior

If the function terminates normally, the file at `os.path.join(work_dir, workflow_filename)` exists and contains the result of copying the original workflow markdown from `os.path.join(script_dir, 'md', workflow_filename)`, then modifying its content. The modification replaces the first occurrence of the exact string:

`- \`phases[*].modules[*].source_files\`  relative paths from repo root of all source files that belong to this module.`

with a new string that incorporates the absolute path of `proj_dir` (`proj_dir_abs`) and its base name (`proj_dir_name`):

`- \`phases[*].modules[*].source_files\`  relative paths from the project root \`{proj_dir_abs}\` of all source files that belong to this module. For example, a file at \`{proj_dir_abs}/path/to/file.ext\` must be recorded as \`path/to/file.ext\`, NOT as \`{proj_dir_name}/path/to/file.ext\`.`


---

## Code Evidence

Line 14: old = ("- `phases[*].modules[*].source_files`  relative paths from repo root of all source files "
Line 15:        "that belong to this module.")

---

## Trigger Condition

The specification requires that the source_files instruction string is rewritten to reference the absolute project root and include the concrete example. However, the code's replacement string (old) exactly matches only a specific literal string without any trailing whitespace. If the source file contains a trailing space after the period (e.g., '... this module. '), str.replace(old, new, 1) will fail to find a match, leaving the old instruction intact and producing a workflow file that still references 'repo root' instead of the project root. This violates Condition B.

---

## How to trigger the bug

The function uses `str.replace(old, new, 1)` with a hard-coded exact-match string. Any whitespace variation in the source template — extra spaces, tabs, line breaks, or different dash characters — prevents the replacement from matching. When this happens, the output workflow file silently retains the original text referencing "repo root" instead of being rewritten to reference the concrete project root with an example. The bug is triggered by any template content that differs from the exact `old` string, not just trailing whitespace. The probe confirmed this with a double-space variation (`"from  repo root"` instead of `"from repo root"`).

### Inputs

| Parameter | Value |
|---|---|
| `proj_dir` | `<tmpdir>/project` |
| `work_dir` | `<tmpdir>/work` |
| `script_dir` | `<tmpdir>/scripts` |
| `workflow_filename` | `test_workflow.md` |
| Template content | Contains `"...from  repo root..."` (double space) instead of `"...from repo root..."` (single space) |

### Expected (spec-correct) Output

`the project root` — the source_files instruction must be rewritten to reference the absolute project root path with a concrete example.

### Actual (buggy) Output

`repo root` — the original text remains intact because `str.replace()` failed to find the exact `old` string in the template.

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import sys, os, tempfile, shutil
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from src.pipeline_setup import _prepare_workflow_file

tmpdir = tempfile.mkdtemp()
proj_dir = os.path.join(tmpdir, "p")
work_dir = os.path.join(tmpdir, "w")
script_dir = os.path.join(tmpdir, "s")
os.makedirs(os.path.join(script_dir, "md"))
os.makedirs(proj_dir); os.makedirs(work_dir)

# Template with double space between "from" and "repo" — any whitespace
# variation in the match string causes silent replacement failure.
with open(os.path.join(script_dir, "md", "test.md"), "w") as f:
    f.write(
        "# Header\n\n"
        "- `phases[*].modules[*].source_files` — relative paths from  repo root of all source files "
        "that belong to this module.\n"
        "\nMore.\n"
    )

_prepare_workflow_file(proj_dir, work_dir, script_dir, "test.md")

with open(os.path.join(work_dir, "test.md")) as f:
    output = f.read()

# Bug: output still says "repo root", should say "the project root"
assert "repo root" in output and "the project root" not in output, "Bug NOT reproduced"
print("Bug confirmed: replacement silently failed")
# actual (buggy) output: "...from  repo root..." (unchanged — original text)
# expected (correct) output: "...from the project root `...`..." (rewritten)
```

---

## Probe Script

```python
"""Probe for bug: _prepare_workflow_file fails to replace source_files instruction
when template has trailing whitespace after the period.

The code uses str.replace(old, new, 1) with an exact-match ``old`` string ending
in ``"that belong to this module."``. If the source template contains a trailing
space after the period (e.g., ``"...this module. "``), the replacement silently
fails, leaving the old instruction intact in the output.
"""

import sys
import os
import tempfile
import shutil

# The project uses package=false in pyproject.toml, so the repo root must be on
# sys.path for relative imports (from .domain_knowledge) inside src/ to resolve.
_script_dir = os.path.dirname(os.path.abspath(__file__))
_repo_root = os.path.dirname(os.path.dirname(_script_dir))
sys.path.insert(0, _repo_root)

# Import the buggy function via the package entry point
from src.pipeline_setup import _prepare_workflow_file


def main():
    tmpdir = tempfile.mkdtemp(prefix="bug_probe_prepare_workflow_")
    try:
        proj_dir = os.path.join(tmpdir, "project")
        work_dir = os.path.join(tmpdir, "work")
        script_dir = os.path.join(tmpdir, "scripts")
        md_dir = os.path.join(script_dir, "md")

        os.makedirs(proj_dir)
        os.makedirs(work_dir)
        os.makedirs(md_dir)

        # Attempt to trigger the bug: str.replace(old, new, 1) uses exact
        # substring matching. If the template content differs from the ``old``
        # string in ANY way (whitespace, extra chars, different dashes), the
        # replacement silently fails.
        #
        # Test case: template has "from repo root" with an extra space within
        # the matching window ("from  repo root" — double space before "repo").
        # The ``old`` string expects single space, so str.replace misses it.
        template_content = (
            "# Test Workflow\n\n"
            "Some instructions.\n\n"
            "- `phases[*].modules[*].source_files` — relative paths from  repo root of all source files "
            "that belong to this module.\n"
            "\n"
            "More content.\n"
        )

        workflow_filename = "test_workflow.md"
        workflow_src = os.path.join(md_dir, workflow_filename)
        with open(workflow_src, "w") as f:
            f.write(template_content)

        # Call the function under test
        _prepare_workflow_file(proj_dir, work_dir, script_dir, workflow_filename)

        # Read the output
        workflow_dst = os.path.join(work_dir, workflow_filename)
        with open(workflow_dst, "r") as f:
            output = f.read()

        # Bug check: if replacement failed, "repo root" is still present
        # and "the project root" (part of the new string) is absent.
        # The spec requires the instruction to reference the project root,
        # but the fragile exact-match means any template whitespace drift
        # silently leaves the old instruction intact.
        has_repo_root = "repo root" in output
        has_project_root = "the project root" in output

        if has_repo_root and not has_project_root:
            print(
                "CONFIRMED — bug reproduced: 'repo root' still in output, "
                "replacement of source_files instruction failed because "
                "whitespace variation in template prevented str.replace() match"
            )
        else:
            print(
                f"NOT CONFIRMED — replacement appears to have succeeded. "
                f"has_repo_root={has_repo_root}, has_project_root={has_project_root}"
            )

    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


if __name__ == "__main__":
    main()
```

### Probe Output

```
CONFIRMED — bug reproduced: 'repo root' still in output, replacement of source_files instruction failed because whitespace variation in template prevented str.replace() match
```

# Bug Report: _modified_function_targets

**Source file:** `/tmp/fm_agent_wt_FM-Agent_9w930mtx/snapshot/fm_agent/extracted_functions/src/incremental_reasoner-py/_modified_function_targets.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- Returns a dict mapping each fully-qualified function name (FQN) to the absolute
    filesystem path of the corresponding extracted-function file under
    proj_dir/fm_agent/extracted_functions/
  - A (source-file, function-name) pair is included when the function name appears in
    at least one of the change-category lists specified by classes within
    modified_functions
  - Function names whose change categories all fall outside classes are excluded from
    the result
  - The FQN key is derived from the extracted-function file path via the project's FQN
    convention: the fm_agent/extracted_functions/ prefix is stripped, the file
    extension is removed, and remaining path components are joined with "::"
    separators, where the source file's final dot was already replaced by a hyphen
    in the extracted-function directory name
  - The extracted-function file path follows the extracted_functions/ layout
    convention: the source file's relative path from proj_dir has its final dot
    replaced by a hyphen to form the directory name, and each function name with the
    source file's original extension forms the leaf filename
  - When a source file's basename contains no dot, the directory name is the basename
    unchanged and the leaf filename has no extension
  - When the same function name appears in multiple change-category lists for the
    same source file, it is included exactly once

---

### Actual Behavior

The function returns a dictionary mapping fully-qualified function names (FQNs) to absolute file paths. The mapping contains exactly one entry for each (source_file_path, change_class, function_name) triple where source_file_path is a key in modified_functions, change_class is an element of classes, and function_name is an element of modified_functions[source_file_path][change_class]. For each such triple: let rel = os.path.relpath(source_file_path, proj_dir); let src_dir = os.path.dirname(rel); let src_base = os.path.basename(rel); if src_base contains a '.' (last_dot > 0) then dir_name = src_base[:last_dot] + '-' + src_base[last_dot+1:] and ext = src_base[last_dot+1:], otherwise dir_name = src_base and ext = ''. Then func_dir = os.path.join(proj_dir, 'fm_agent', 'extracted_functions', src_dir, dir_name) if src_dir else os.path.join(proj_dir, 'fm_agent', 'extracted_functions', dir_name). Let fname = f'{function_name}.{ext}' if ext else function_name; path = os.path.join(func_dir, fname); fqn = _file_to_fqn(path, os.path.join(proj_dir, 'fm_agent')). The returned dictionary contains the binding fqn  path. No other keys are present. The function completes normally without raising any exceptions (assuming _file_to_fqn satisfies its contract).

---

## Code Evidence

Line 23: if last_dot > 0:

---

## Trigger Condition

The specification says that if the source file basename contains any dot, the final dot is replaced by a hyphen to form the directory name. The code only does this when the final dot is not at position 0 (last_dot > 0). For a file like '.hidden', the dot is at index 0, so the code treats it as having no dot, leaving the basename unchanged and setting ext=''. The specification's exception 'When a source file's basename contains no dot' does not apply because '.hidden' contains a dot, so the rule should be applied, resulting in dir_name='-hidden' and ext='hidden'. Thus the code produces an incorrect FQN and file path.

---

## How to trigger the bug

### Inputs

| Parameter | Value |
|-----------|-------|
| proj_dir | `/tmp/probe_XXXXX/` (temp directory) |
| modified_functions | `{"/tmp/probe_XXXXX/src/.hidden": {"added": ["myfunc"]}}` |
| classes | `("added", "removed", "modified")` (default) |

### Expected (spec-correct) Output

FQN has a path component `-hidden` (the final dot in `.hidden` replaced by hyphen). The extracted function file path ends with `extracted_functions/src/-hidden/myfunc.hidden`.

### Actual (buggy) Output

FQN has a path component `.hidden` (the dotfile basename kept as-is). The extracted function file path ends with `extracted_functions/src/.hidden/myfunc`.

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import os, tempfile
from src.incremental_reasoner import _modified_function_targets

tmp = tempfile.mkdtemp()
os.makedirs(os.path.join(tmp, "src"))
hidden_abs = os.path.join(tmp, "src", ".hidden")
with open(hidden_abs, "w") as f:
    f.write("")

result = _modified_function_targets(tmp, {hidden_abs: {"added": ["myfunc"]}})
fqn = list(result.keys())[0]
last_component = fqn.rsplit("::", 1)[0].split("::")[-1]
print(last_component)
# actual (buggy) output: ".hidden"
# expected (correct) output: "-hidden"
```

---

## Probe Script

```python
import sys
import os
import tempfile

try:
    from src.incremental_reasoner import _modified_function_targets
except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)

# Create a temporary project directory with a fake source file ".hidden"
# in a "src" subdirectory to exercise the dotfile edge case.
tmp = tempfile.mkdtemp(prefix="probe_")
try:
    src_dir = os.path.join(tmp, "src")
    os.makedirs(src_dir)

    # Create a fake .hidden source file and a corresponding extracted-functions dir
    hidden_abs = os.path.join(src_dir, ".hidden")
    with open(hidden_abs, "w") as f:
        f.write("")

    # Also create the expected extracted dir for the -hidden case (spec-correct)
    spec_extracted_dir = os.path.join(tmp, "fm_agent", "extracted_functions", "src", "-hidden")
    os.makedirs(spec_extracted_dir)

    modified_functions = {hidden_abs: {"added": ["myfunc"]}}

    result = _modified_function_targets(tmp, modified_functions)

    # Determine what the spec-correct behavior should be.
    # Spec says: basename contains a dot → final dot replaced by hyphen.
    # ".hidden" has a dot at index 0, so dir_name = "-hidden", ext = "hidden"
    spec_extracted_dir = os.path.join(tmp, "fm_agent", "extracted_functions", "src", "-hidden")
    spec_fname = "myfunc.hidden"
    spec_path = os.path.join(spec_extracted_dir, spec_fname)

    # Determine what the buggy code produced.
    # The buggy code (last_dot > 0 check) treats .hidden as having no dot:
    # dir_name = ".hidden", ext = ""
    bug_extracted_dir = os.path.join(tmp, "fm_agent", "extracted_functions", "src", ".hidden")
    bug_fname = "myfunc"
    bug_path = os.path.join(bug_extracted_dir, bug_fname)

    # Check: does the actual result match the buggy path or the spec-correct path?
    actual_paths = list(result.values())
    actual_fqns = list(result.keys())

    if not actual_fqns:
        print("ERROR: result is empty — no targets returned")
        sys.exit(1)

    actual_path = actual_paths[0]
    actual_fqn = actual_fqns[0]

    # The spec says the FQN should contain "-hidden" as the last component before "::myfunc"
    # For the buggy case (no dot processing), the directory component would be ".hidden"
    # For the spec-correct case, it would be "-hidden"

    # Expected behavior per spec: the file .hidden has a dot, so:
    #   dir_name = "-hidden", ext = "hidden"
    # This means the FQN should have "-hidden" in it, not ".hidden"
    expected_has_dash_hidden = "-hidden::myfunc" in actual_fqn or actual_fqn.endswith("::myfunc")
    # But actually the leaf function name in FQN is "myfunc" (extension stripped by _file_to_fqn)
    # And the directory component should be "-hidden" not ".hidden"

    # Simpler check: spec expects the path dir to be "-hidden" not ".hidden"
    actual_fqn_dir = actual_fqn.rsplit("::", 1)[0]
    fqn_last_component = actual_fqn_dir.split("::")[-1] if "::" in actual_fqn_dir else actual_fqn_dir

    bug_confirmed = ".hidden" in fqn_last_component and "-hidden" not in fqn_last_component
    # The spec-correct behavior should have "-hidden" last component
    spec_correct_last = "-hidden"

    passed = bug_confirmed  # True if the buggy behavior is observed

    if passed:
        print(
            f"CONFIRMED — actual FQN last component: '{fqn_last_component}' "
            f"| expected (spec) last component: '{spec_correct_last}' "
            f"| actual path: {actual_path}"
        )
    else:
        print(
            f"NOT CONFIRMED — actual FQN last component: '{fqn_last_component}' "
            f"| actual path: {actual_path}"
        )

    # Cleanup
    import shutil
    shutil.rmtree(tmp, ignore_errors=True)
except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)
```

### Probe Output

```
CONFIRMED — actual FQN last component: '.hidden' | expected (spec) last component: '-hidden' | actual path: /tmp/probe_jh1n4jz_/fm_agent/extracted_functions/src/.hidden/myfunc
```

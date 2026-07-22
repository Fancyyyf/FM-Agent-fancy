# Generate Function Specification

A modification has been applied to a codebase to achieve the developer intent below, adding a function that has no behavioral specification yet. Generate its specification from scratch.

- Function fully-qualified name: `src::pipeline_setup-py::_phase_plan_schema_errors` (language: `python`).
- Comment prefix for this language: `#`.
- Known callees of this function: (none).

## Developer intent

# Incremental self-validation intent

Validate all behavioral and correctness impacts introduced between the recorded
FM-Agent baseline and the current checked-out main-derived revision. Regenerate
specifications for changed or relevant functions and verify affected callers.
Pay particular attention to file readiness, incremental reasoning, CLI backend,
codegraph integration, tracing, environment checks, and pipeline setup changes.
Do not modify project source files; write validation artifacts only under the
FM-Agent workspace.

## Function source

```python
def _phase_plan_schema_errors(phases_path):
    """Return human-readable schema errors for phases.json."""
    try:
        with open(phases_path, "r") as f:
            data = json.load(f)
    except OSError as exc:
        return [f"phases.json could not be read: {exc}"]
    except json.JSONDecodeError as exc:
        return [f"phases.json is not valid JSON: {exc}"]

    if not isinstance(data, dict):
        return ["the top-level value must be an object"]

    phases = data.get("phases")
    if not isinstance(phases, list):
        return ['top-level field "phases" must be an array']

    errors = []
    for phase_index, phase in enumerate(phases):
        phase_path = f"phases[{phase_index}]"
        if not isinstance(phase, dict):
            errors.append(f"{phase_path} must be an object")
            continue

        modules = phase.get("modules")
        if not isinstance(modules, list):
            errors.append(f"{phase_path}.modules must be an array")
            continue

        for module_index, module in enumerate(modules):
            module_path = f"{phase_path}.modules[{module_index}]"
            if not isinstance(module, dict):
                errors.append(f"{module_path} must be an object")
                continue

            module_name = module.get("name", "")
            context = (
                f"{module_path} ({module_name!r})"
                if module_name
                else module_path
            )

            if "source_files" not in module:
                errors.append(f"{context}.source_files is missing")
                continue

            source_files = module["source_files"]
            if not isinstance(source_files, list):
                errors.append(f"{context}.source_files must be an array")
                continue

            for source_index, source_file in enumerate(source_files):
                if not isinstance(source_file, str):
                    errors.append(
                        f"{context}.source_files[{source_index}] must be a string"
                    )

    return errors
```

## Specs of this function's callers

### src::pipeline_setup-py::_phase_plan_complete

# [SPEC]
# Unit: src/pipeline_setup-py/_phase_plan_complete.py
#
# _phase_plan_complete(work_dir) -> bool
#
# Pre-condition:
#   - work_dir is a string path to an existing directory.
#
# Post-condition:
#   - Returns True when the file phases.json exists under work_dir, is a
#     regular file, its content parses as valid JSON, and it conforms to the
#     required schema (as determined by _phase_plan_schema_errors).
#   - Returns False when phases.json does not exist under work_dir, is not a
#     regular file, does not parse as valid JSON, or does not conform to the
#     required schema.
#   - The return value is idempotent for the same filesystem state: repeated
#     calls with the same work_dir and same file content yield the same boolean
#     result.
# [SPEC]

### src::pipeline_setup-py::_run_generate_phases

# [SPEC]
# Unit: src/pipeline_setup-py/_run_generate_phases.py
#
# _run_generate_phases(proj_dir, work_dir, script_dir, is_incremental=False, resume=False, submodules=None) -> None
#
# Pre-condition:
#   - proj_dir, work_dir, and script_dir refer to existing directory paths
#   - is_incremental is a boolean; when truthy, a pre-existing phases.json under work_dir is updated in place rather than regenerated from scratch
#   - resume is a boolean
#   - submodules is None or a non-empty iterable of subdirectory name strings relative to proj_dir
#
# Post-condition:
#   - On normal return: phases.json exists under work_dir and conforms to the phases.json schema
#   - When resume is truthy and phases.json already satisfies the pipeline's completeness criteria, the function returns without producing or modifying any file
#   - When submodules is provided: phases.json covers all source files under the specified subdirectories of proj_dir; source files outside those subdirectories are neither added nor required to be present
#   - When is_incremental is truthy: a valid phases.json already present under work_dir may be accepted without modification if it covers all current source files, even when its modification timestamp has not changed
#   - If valid phases.json is not produced or confirmed after a configurable maximum number of retry attempts, the function prints a diagnostic message to stdout identifying the failed stage and the trace directory, then calls sys.exit(1)
#   - When a non-final attempt fails to produce valid phases.json, the function does not call sys.exit(1) — it waits a fixed interval before retrying
# [SPEC]

## What callers expect from this function (from their [INFO] blocks)

Your generated [SPEC] must be consistent with these expectations.

### According to src::pipeline_setup-py::_phase_plan_complete

# _phase_plan_schema_errors(file_path) -> any
#   Pre-condition: file_path is a string path to a file.
#   Post-condition: Returns a truthy value (e.g., a non-empty error list or
#     error message string) if the file does not exist, is not a regular file,
#     does not contain valid JSON, or fails to conform to the required schema.
#   - Returns a falsey value (e.g., None or empty list) when the file exists,
#     is a regular file, parses as valid JSON, and fully conforms to the
#     required schema.

## Steps

1. Read `fm_agent/spec_prompts/system_prompt.md` for the exact [SPEC]/[INFO] format rules used by this project.
2. Produce the COMPLETE [SPEC] block describing this function's behavior — the `[SPEC]` ... `[SPEC]` block only, markers included, every line prefixed with `#`, and NO source code.
3. This function has no callees, so produce no [INFO] block.
4. Write your answer to `fm_agent/spec_generate_215.json` as a JSON object with keys:
   - "spec_updated": boolean — true when you produced a [SPEC] block.
   - "new_spec": string — the full [SPEC] block.
   - "info_updated": boolean — true when you produced an [INFO] block.
   - "new_info": string — the full [INFO] block, or "" if none.
   - "updated_callees": array of callee name strings recorded in [INFO], or [].
   Write ONLY that JSON file; do not modify any other project files.

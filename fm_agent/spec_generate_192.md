# Generate Function Specification

A modification has been applied to a codebase to achieve the developer intent below, adding a function that has no behavioral specification yet. Generate its specification from scratch.

- Function fully-qualified name: `src::incremental_reasoner-py::_src_rel_to_func_dir` (language: `python`).
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
def _src_rel_to_func_dir(proj_dir, abs_src):
    """(func_dir, ext) for a source file: the extracted-functions directory that
    holds its functions (``.../loader-cpp``) and the source extension."""
    extracted_base = os.path.join(proj_dir, "fm_agent", "extracted_functions")
    rel = os.path.relpath(abs_src, proj_dir)
    src_dir = os.path.dirname(rel)
    src_base = os.path.basename(rel)
    last_dot = src_base.rfind(".")
    if last_dot > 0:
        dir_name = src_base[:last_dot] + "-" + src_base[last_dot + 1:]
        ext = src_base[last_dot + 1:]
    else:
        dir_name = src_base
        ext = ""
    func_dir = os.path.join(extracted_base, src_dir, dir_name) if src_dir else os.path.join(extracted_base, dir_name)
    return func_dir, ext
```

## Specs of this function's callers

### src::incremental_reasoner-py::_modified_function_targets

# [SPEC]
# Unit: fm_agent/extracted_functions/src/incremental_reasoner-py/_modified_function_targets.py
#
# _modified_function_targets(proj_dir, modified_functions, classes=("added", "removed", "modified")) -> dict[str, str]
#
# Pre-condition:
#   - proj_dir is an absolute path to a project root directory whose
#     fm_agent/extracted_functions/ subdirectory exists
#   - modified_functions is a dict mapping absolute source-file paths to dicts, where
#     each inner dict has string-valued keys drawn from {"added", "removed", "modified"}
#     with list-of-string values (function names declared in that source file)
#   - classes is a non-empty tuple of string-valued change-category labels drawn from
#     {"added", "removed", "modified"}
#
# Post-condition:
#   - Returns a dict mapping each fully-qualified function name (FQN) to the absolute
#     filesystem path of the corresponding extracted-function file under
#     proj_dir/fm_agent/extracted_functions/
#   - A (source-file, function-name) pair is included when the function name appears in
#     at least one of the change-category lists specified by classes within
#     modified_functions
#   - Function names whose change categories all fall outside classes are excluded from
#     the result
#   - The FQN key is derived from the extracted-function file path via the project's FQN
#     convention: the fm_agent/extracted_functions/ prefix is stripped, the file
#     extension is removed, and remaining path components are joined with "::"
#     separators, where the source file's final dot was already replaced by a hyphen
#     in the extracted-function directory name
#   - The extracted-function file path follows the extracted_functions/ layout
#     convention: the source file's relative path from proj_dir has its final dot
#     replaced by a hyphen to form the directory name, and each function name with the
#     source file's original extension forms the leaf filename
#   - When a source file's basename contains no dot, the directory name is the basename
#     unchanged and the leaf filename has no extension
#   - When the same function name appears in multiple change-category lists for the
#     same source file, it is included exactly once
#   - For each source file, the function directory is resolved via _src_rel_to_func_dir,
#     and the available extracted-function files are indexed by bare method name via
#     _extracted_files_by_method
#   - For each changed function name, the function first looks for an exact match in the
#     method-name index; if no match is found, it strips a trailing “_\d+” suffix (a
#     regex deduplication disambiguator) from the name and retries with the resulting
#     stem
#   - When a bare name or its stem matches multiple extracted-function files (e.g.,
#     because two classes in the source file define a method with the same name), every
#     matching file is included in the result
# [SPEC]

### src::incremental_reasoner-py::_reconcile_extracted_dir

# [SPEC]
# Unit: src/incremental_reasoner-py/_reconcile_extracted_dir.py
#
# _reconcile_extracted_dir(proj_dir, abs_src) -> None
#
# Pre-condition:
#   - proj_dir is an absolute path to the project root directory
#   - abs_src is an absolute path to a source file within proj_dir
#
# Post-condition:
#   - Let (func_dir, ext) be the pair that maps abs_src to the extracted-functions
#     directory and source extension via the same naming convention used by
#     run_extraction. If func_dir is not an existing directory on disk, no
#     filesystem changes occur and the function returns.
#   - Otherwise, the set of expected extracted-function files for abs_src is
#     determined:
#     * When abs_src exists on disk and its file extension maps to a language
#       recognized by the project's language registry, the expected files are
#       derived from the current function spans of abs_src. Each span's
#       deduplicated identifier forms an expected filename: the identifier
#       suffixed with ".<ext>" when ext is non-empty, or the bare identifier
#       when ext is empty. The span boundaries are computed with the same
#       backend (codegraph when it indexes the file, otherwise regex) that
#       run_extraction uses.
#     * When abs_src does not exist on disk, or when its extension is not
#       recognized, the set of expected files is empty.
#   - Every file reachable by recursively walking func_dir whose absolute path
#     does not match an expected file path is deleted. Expected files are
#     preserved with their contents unchanged.
#   - After file deletion, every subdirectory of func_dir — excluding func_dir
#     itself — that contains neither files nor subdirectories is removed.
# [SPEC]

## What callers expect from this function (from their [INFO] blocks)

Your generated [SPEC] must be consistent with these expectations.

### According to src::incremental_reasoner-py::_reconcile_extracted_dir

# _src_rel_to_func_dir(proj_dir, abs_src) -> (str, str)
#   Pre-condition: proj_dir is an absolute project root path, abs_src is an
#     absolute source file path within proj_dir
#   Post-condition: Returns (func_dir, ext) where func_dir is the directory
#     path under proj_dir/fm_agent/extracted_functions/ that run_extraction
#     would use for abs_src, derived by replacing the last dot in the source
#     filename with a hyphen to form the leaf directory name, preserving the
#     relative directory hierarchy from proj_dir. ext is the portion of the
#     source filename after the last dot (the file extension), or an empty
#     string when the filename contains no dot.

## Steps

1. Read `fm_agent/spec_prompts/system_prompt.md` for the exact [SPEC]/[INFO] format rules used by this project.
2. Produce the COMPLETE [SPEC] block describing this function's behavior — the `[SPEC]` ... `[SPEC]` block only, markers included, every line prefixed with `#`, and NO source code.
3. This function has no callees, so produce no [INFO] block.
4. Write your answer to `fm_agent/spec_generate_192.json` as a JSON object with keys:
   - "spec_updated": boolean — true when you produced a [SPEC] block.
   - "new_spec": string — the full [SPEC] block.
   - "info_updated": boolean — true when you produced an [INFO] block.
   - "new_info": string — the full [INFO] block, or "" if none.
   - "updated_callees": array of callee name strings recorded in [INFO], or [].
   Write ONLY that JSON file; do not modify any other project files.

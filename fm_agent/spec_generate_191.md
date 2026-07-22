# Generate Function Specification

A modification has been applied to a codebase to achieve the developer intent below, adding a function that has no behavioral specification yet. Generate its specification from scratch.

- Function fully-qualified name: `src::incremental_reasoner-py::_extracted_files_by_method` (language: `python`).
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
def _extracted_files_by_method(func_dir):
    """``{key: [abs_path, ...]}`` for every extracted-function file under
    ``func_dir``, walked recursively. Each file is registered under BOTH keys so a
    caller can look it up whichever kind of name it holds:

      - its bare stem (``Flush``) — the regex change detector reports names
        without a class, so a bare name matches every same-named member;
      - its class-qualified identifier (``LocalStorage::Flush``) — scope ranking
        gets qualified names from codegraph spans, so this gives an exact match.

    A free function (``func_dir/foo.ext``) has identical stem and identifier, so it
    is registered once."""
    index = defaultdict(list)
    if not os.path.isdir(func_dir):
        return index
    for root, _dirs, fnames in os.walk(func_dir):
        for fn in fnames:
            abs_path = os.path.join(root, fn)
            # Flat layout: the filename stem is the full identifier, keeping any
            # "::" ("LocalStorage::Flush"). Register it under both the full
            # identifier and the bare tail ("Flush") so both codegraph's qualified
            # names and the regex detector's bare names resolve. (os.walk still
            # tolerates a legacy nested file, whose stem is already bare.)
            stem = fn[: fn.rfind(".")] if "." in fn else fn
            index[stem].append(abs_path)
            bare = stem.split("::")[-1]
            if bare != stem:
                index[bare].append(abs_path)
    return index
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

### src::incremental_reasoner-py::collect_relevent_function_scope

# [SPEC]
# Unit: fm_agent/extracted_functions/src/incremental_reasoner-py/collect_relevent_function_scope.py
#
# collect_relevent_function_scope(proj_dir, developer_intent, changed_functions, range=None) -> list[str]
#
# Pre-condition:
#   - proj_dir is a path to a project directory whose fm_agent/ subdirectory contains phases.json
#     (with a "phases" list of phase objects, each containing a "modules" list) and extracted_functions/
#   - developer_intent is a non-empty string describing the modification goal
#   - changed_functions is a dict mapping absolute source file paths to dicts with string-list values
#     under at least the keys "added", "modified", and "removed"
#   - range is None or a non-negative integer
#
# Post-condition:
#   - Returns a list of paths, each relative to the extracted_functions/ directory, ordered by
#     descending relevance to developer_intent; paths with equal relevance are ordered lexicographically
#   - Every returned path refers to an existing regular file under extracted_functions/
#   - When range is not None, the returned list has length ≤ range
#   - Returns an empty list when phases.json defines no modules, or when no module is selected
#     by the relevance assessment
#   - A module is selected when EITHER its natural-language description (as recorded in phases.json)
#     is assessed as relevant to the developer intent, OR the module contains at least one source file
#     whose path, relativized against proj_dir, matches a key in changed_functions
#   - Within each selected module, a source file is included only when its content is assessed as
#     relevant to the developer intent, EXCEPT that every source file present in changed_functions
#     is included unconditionally
#   - When the per-module file-relevance assessment cannot be obtained, every source file in that
#     module is included
#   - Within each included source file, the set of extracted functions whose relevance scores
#     (computed from heuristic signals derived from developer_intent) rank within the top of that file
#     are included
#   - When per-file function ranking is unavailable for an included source file, every extracted
#     function from that file is included
#   - Multiple extracted-function files mapping to the same source-level function are deduplicated,
#     keeping only the occurrence with the highest relevance score
# [SPEC]

## Steps

1. Read `fm_agent/spec_prompts/system_prompt.md` for the exact [SPEC]/[INFO] format rules used by this project.
2. Produce the COMPLETE [SPEC] block describing this function's behavior — the `[SPEC]` ... `[SPEC]` block only, markers included, every line prefixed with `#`, and NO source code.
3. This function has no callees, so produce no [INFO] block.
4. Write your answer to `fm_agent/spec_generate_191.json` as a JSON object with keys:
   - "spec_updated": boolean — true when you produced a [SPEC] block.
   - "new_spec": string — the full [SPEC] block.
   - "info_updated": boolean — true when you produced an [INFO] block.
   - "new_info": string — the full [INFO] block, or "" if none.
   - "updated_callees": array of callee name strings recorded in [INFO], or [].
   Write ONLY that JSON file; do not modify any other project files.

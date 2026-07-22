# Generate Function Specification

A modification has been applied to a codebase to achieve the developer intent below, adding a function that has no behavioral specification yet. Generate its specification from scratch.

- Function fully-qualified name: `src::incremental_reasoner-py::_reconcile_extracted_dir` (language: `python`).
- Comment prefix for this language: `#`.
- Known callees of this function: _function_spans, _src_rel_to_func_dir.

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
def _reconcile_extracted_dir(proj_dir, abs_src):
    """Delete extracted-function files under abs_src's function directory that
    codegraph no longer produces for it, then prune emptied directories.

    ``valid`` is computed with the same backend (codegraph when it indexes the
    file, else regex) that run_extraction used to write the files, so their
    identifiers — and therefore the on-disk layout — agree; only genuinely orphaned
    files are removed. A source file that no longer exists yields an empty ``valid``
    set, so all of its extracted files are removed.
    """
    func_dir, ext = _src_rel_to_func_dir(proj_dir, abs_src)
    if not os.path.isdir(func_dir):
        return

    valid = set()
    lang_key = EXT_TO_LANG.get(ext)
    if lang_key and os.path.isfile(abs_src):
        spans, _raw = _function_spans(abs_src, lang_key, proj_dir)
        for ident, _s, _e in spans:
            # ident is the class-qualified, deduped identifier written by
            # run_extraction as a flat file that keeps the "::" in its name.
            path = os.path.join(func_dir, ident) + (f".{ext}" if ext else "")
            valid.add(os.path.abspath(path))

    for root, _dirs, fnames in os.walk(func_dir):
        for fn in fnames:
            abs_path = os.path.abspath(os.path.join(root, fn))
            if abs_path not in valid:
                os.remove(abs_path)

    # Prune empty directories left behind (deepest first).
    for root, _dirs, _files in os.walk(func_dir, topdown=False):
        if root != func_dir and os.path.isdir(root) and not os.listdir(root):
            os.rmdir(root)
```

## Specs of this function's callers

### src::incremental_reasoner-py::_remove_stale_extracted

# [SPEC]
# _remove_stale_extracted(proj_dir, modified_functions) -> None
#
# Pre-condition:
#   - proj_dir is an absolute path to the project root directory, under which the child directory fm_agent/ exists with sub-directory extracted_functions/ and a phases.json file.
#   - modified_functions is a dict whose keys are absolute source-file paths (the values are not used by this function).
#
# Post-condition:
#   - For every absolute source-file path that is either a key in modified_functions or listed in the "source_files" entries of all phases loaded from phases.json, the extracted-function tree under fm_agent/extracted_functions/ associated with that source file is reconciled with the current codegraph output. Any extracted function file or directory that no longer corresponds to a current source function (including when the source file itself is absent) is deleted, and any empty parent directories are pruned.
#   - Files and directories under fm_agent/extracted_functions/ that correspond to source files not in the union of modified_functions keys and phases.json entries are unchanged.
# [SPEC]

## Steps

1. Read `fm_agent/spec_prompts/system_prompt.md` for the exact [SPEC]/[INFO] format rules used by this project.
2. Produce the COMPLETE [SPEC] block describing this function's behavior — the `[SPEC]` ... `[SPEC]` block only, markers included, every line prefixed with `#`, and NO source code.
3. Because this function has callees, also produce an [INFO] block recording the expected behavioral spec of each callee it depends on (the `[INFO]` ... `[INFO]` block only, markers included, every line prefixed with `#`), and list the names of the callees you recorded.
4. Write your answer to `fm_agent/spec_generate_142.json` as a JSON object with keys:
   - "spec_updated": boolean — true when you produced a [SPEC] block.
   - "new_spec": string — the full [SPEC] block.
   - "info_updated": boolean — true when you produced an [INFO] block.
   - "new_info": string — the full [INFO] block, or "" if none.
   - "updated_callees": array of callee name strings recorded in [INFO], or [].
   Write ONLY that JSON file; do not modify any other project files.

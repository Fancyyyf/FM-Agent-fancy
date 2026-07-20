# [SPEC]
# Unit: fm_agent/extracted_functions/src/entry_reasoning_pipeline-py/_run_entry_pipeline_inner.py
#
# _run_entry_pipeline_inner(proj_dir, work_dir, entry_func, end_funcs, resume, domain_knowledge_files=None, one_phase=False, extra_call_edges_path=None, only_spec=False) -> None
#
# Pre-condition:
#   - proj_dir is an absolute path to an existing directory
#   - work_dir is the path <proj_dir>/fm_agent
#   - entry_func is a non-empty FQN string
#   - domain_knowledge_files, if provided, is a non-empty collection of file paths
#
# Post-condition:
#   - proj_dir is never mutated by this function or any callee transitively invoked
#   - A temporary directory at <proj_dir>.fm-entry-run is created during execution and destroyed before return, regardless of success or failure
#   - The set of functions operated on is the subset reachable from entry_func via the static call graph; when end_funcs is non-empty, the set is further restricted to functions on at least one call-chain path from entry_func to some member of end_funcs
#   - On successful completion, work_dir contains the complete fm_agent/ output produced by running the standard pipeline on the trimmed project copy
#   - On failure, any partial fm_agent/ results already produced within the temporary run directory are copied to work_dir before the temporary directory is destroyed
#   - The number of MISMATCH verdicts found in work_dir/logic_verification_results/ is printed to stdout on every run
#   - When extra_call_edges_path is provided, its supplemental call edges contribute to the reachability analysis used to determine the function subset
# [SPEC]

# [INFO]
# load_call_edges(extra_call_edges_path) -> Optional[list]
#   Pre-condition: extra_call_edges_path is a path to a JSON file or None
#   Post-condition: When extra_call_edges_path is a valid path to a JSON file, returns the parsed call-edges structure; when the path is None or the file is absent, returns an empty or None value without raising
# [SPLIT]
# _select_functions_by_source(proj_dir, entry_func, end_funcs, extra_call_edges) -> (dict[str, set[str]], dict[str, set[str]])
#   Pre-condition: proj_dir is an existing project directory; entry_func is a non-empty FQN; end_funcs is a possibly-empty collection of FQNs
#   Post-condition: Returns two dicts mapping source-file relative paths to sets of function FQN strings; the first dict maps each source file to all function names it contains; the second dict maps each source file to only the function names that are on at least one call-chain path from entry_func (and, when end_funcs is non-empty, from entry_func to some end_func); the selection uses a temporary workspace that is discarded before return
# [SPLIT]
# _make_run_copy(proj_dir, run_dir) -> None
#   Pre-condition: proj_dir is an existing directory; run_dir is a non-existing or writable directory path
#   Post-condition: run_dir contains a full recursive copy of proj_dir, including an existing fm_agent/ subdirectory if one was present in proj_dir
# [SPLIT]
# try_codegraph_init(run_dir) -> None
#   Pre-condition: run_dir is an existing directory
#   Post-condition: If the codegraph tool is installed, a codegraph index is built on run_dir; if codegraph is absent, the call returns without raising an exception
# [SPLIT]
# _trim_project_in_place(run_dir, all_by_source, keep_by_source) -> None
#   Pre-condition: run_dir is a directory containing source files; all_by_source maps source-file relative paths to sets of all function names; keep_by_source maps source-file relative paths to sets of function names to preserve
#   Post-condition: Within run_dir, every source file has all function bodies whose names appear in all_by_source but not in keep_by_source removed; source files whose keep_by_source set is empty are deleted; non-function lines (comments, imports, top-level statements) are preserved
# [SPLIT]
# _entry_func_source_rel(entry_func) -> str
#   Pre-condition: entry_func is a valid FQN string
#   Post-condition: Returns the source-file relative path (using "/" separators) that contains entry_func, derived by reversing the FQN-to-extracted-file-path convention
# [SPLIT]
# run_pipeline(run_dir, resume, required_source_files, domain_knowledge_files, one_phase, extra_call_edges_path, only_spec) -> None
#   Pre-condition: run_dir is an existing project directory with valid source files
#   Post-condition: Executes the full FM-Agent pipeline (phases 1-5) on run_dir; the source file listed in required_source_files is force-included in phases.json regardless of heuristics; all outputs are written under <run_dir>/fm_agent/; on failure, partial results are preserved under that directory
# [SPLIT]
# _count_mismatches(dir_path) -> int
#   Pre-condition: dir_path is a path that may or may not exist
#   Post-condition: When dir_path exists and is a directory, returns the count of JSON files under it whose verdict field is "MISMATCH"; when dir_path does not exist, returns 0 without raising
# [INFO]

def _run_entry_pipeline_inner(
    proj_dir,
    work_dir,
    entry_func,
    end_funcs,
    resume,
    domain_knowledge_files=None,
    one_phase=False,
    extra_call_edges_path=None,
    only_spec=False,
):
    """Body of run_entry_pipeline; runs with the entry source file exempted."""
    # 1. Selection: extract fresh into a temp workspace and build the call graph.
    extra_call_edges = load_call_edges(extra_call_edges_path)
    all_by_source, keep_by_source = _select_functions_by_source(
        proj_dir,
        entry_func,
        end_funcs,
        extra_call_edges=extra_call_edges,
    )

    # 2. Copy the sources into a separate run directory, then trim that copy.
    # proj_dir is left untouched throughout.
    run_dir = proj_dir + ".fm-entry-run"
    run_work_dir = os.path.join(run_dir, "fm_agent")
    # _make_run_copy brings along an existing fm_agent/, so a resumed run finds
    # the prior state in run_dir without any extra seeding here.
    _make_run_copy(proj_dir, run_dir)
    try:
        # Build the codegraph index on the run copy before trimming so that
        # _trim_project_in_place detects function names/spans with the same
        # codegraph backend that _select_functions_by_source used to produce
        # keep_by_source. Without it the trim would fall back to the regex
        # extractor and could disagree with the selection (mismatched names or
        # spans -> wrong functions kept/removed). Non-fatal: skips silently if
        # codegraph is not installed (selection then also used regex, so the two
        # stay consistent). run_pipeline rebuilds the index again after the trim
        # edits these sources, so extraction sees the trimmed tree, not this one.
        try_codegraph_init(run_dir)
        _trim_project_in_place(run_dir, all_by_source, keep_by_source)

        # 3. Run the standard pipeline directly on the run copy.
        # Imported lazily to avoid a circular import (main imports
        # run_entry_pipeline at module load).
        from main import run_pipeline

        # Force the entry point's source file into phases.json even if the setup
        # agent omits it (e.g. because it looks like a test), so run_pipeline
        # always extracts and reasons about the entry function.
        run_pipeline(
            run_dir,
            resume=resume,
            required_source_files=[_entry_func_source_rel(entry_func)],
            domain_knowledge_files=domain_knowledge_files,
            one_phase=one_phase,
            extra_call_edges_path=extra_call_edges_path,
            only_spec=only_spec,
        )
    finally:
        # 4. Copy the generated fm_agent/ back into proj_dir, then discard the
        # run directory. Runs even on failure so partial results are preserved.
        if os.path.isdir(run_work_dir):
            if os.path.isdir(work_dir):
                shutil.rmtree(work_dir)
            shutil.copytree(run_work_dir, work_dir, symlinks=True)
            print(f"[EntryPipeline] Copied generated fm_agent/ to {work_dir}.")
        shutil.rmtree(run_dir, ignore_errors=True)

    # Report the bug count: the number of MISMATCH verdicts the reasoner wrote
    # into fm_agent/logic_verification_results/.
    mismatches = _count_mismatches(os.path.join(work_dir, "logic_verification_results"))
    print(f"[EntryPipeline] Bugs (mismatches): {mismatches}")

    print(f"[EntryPipeline] Done. Results in {work_dir}.")

# [SPEC]
# Unit: src/incremental_reasoner-py/run_incremental_pipeline.py
#
# run_incremental_pipeline(proj_dir, intent_file_path, old_commit_id,
#                          domain_knowledge_files=None, submodules=None,
#                          one_phase=False, extra_call_edges_path=None)
#   -> list[str] | None
#
# Pre-condition:
#   - proj_dir is a path to an existing directory containing source code under
#     version control; fm_agent/ is a writable subdirectory within it.
#   - intent_file_path is a string; when non-empty and pointing to a regular
#     file, its content describes the developer's modification goal.
#   - old_commit_id is a string identifying a prior commit in proj_dir's git
#     repository.
#   - domain_knowledge_files, when not None, is a list of paths to Markdown
#     files providing project-specific domain context.
#   - submodules, when not None, is a list of subdirectory paths within proj_dir
#     to scope analysis to.
#   - one_phase is a bool (default False) controlling whether all source files
#     are placed into a single phase.
#   - extra_call_edges_path, when not None, is a path to a JSON file defining
#     supplemental call-graph edges.
#
# Post-condition:
#   - If proj_dir has no previous full-run baseline (fm_agent/phases.json absent
#     or fm_agent/extracted_functions/ incomplete given submodules), delegates
#     the entire pipeline to a full run via run_pipeline() with the same
#     arguments and returns None.
#   - If intent_file_path does not refer to an existing regular file, or the
#     file content is empty after whitespace stripping, logs an error and
#     returns None without modifying any project or fm_agent/ file.
#   - Before producing any new output, removes all files under
#     fm_agent/logic_verification_results/ and fm_agent/bug_validation/, and
#     removes incremental scope-selection and spec-update artifacts prefixed
#     with "select_relevant_", "relevant_", and "spec_update_" from fm_agent/.
#   - Regenerates fm_agent/phases.json from the current working tree.
#   - Re-extracts every function from the current code, then restores the
#     captured [SPEC] and [INFO] blocks from the prior run onto each function
#     whose body is identical between old_commit_id and the current working
#     tree.
#   - Produces a mapping from each changed source-file path to the sets of
#     function names added, modified, or removed since old_commit_id; deletes
#     extracted-function files for removed functions.
#   - Produces a ranked list of extracted-function relative paths whose
#     implementations are judged relevant to the developer intent.
#   - For every function that is either changed (added or modified) or appears
#     in the relevance-ranked list, re-evaluates whether its [SPEC] and/or
#     [INFO] blocks need updating to reflect the current code and intent;
#     when a callee's [SPEC] changes, propagates the update to every caller's
#     [INFO] block. Writes the set of files whose specs were modified to
#     fm_agent/incremental_updated_specs.json.
#   - Runs verification on the affected subset: every changed function, every
#     function with an updated spec, and every function that calls a callee
#     whose spec was updated. Returns a sorted list of extracted-function
#     relative paths for which the reasoner reported a spec-to-code mismatch
#     (MISMATCH verdict) and bug validation subsequently confirmed the
#     violation. Returns an empty list when no such violations are confirmed.
#   - Does not modify any file under proj_dir outside of fm_agent/.
# [SPEC]

# [INFO]
# check_last_run_existence(proj_dir, submodules=None) -> bool
#   Pre-condition: proj_dir is a valid directory path; submodules is None or
#     a list of subdirectory names
#   Post-condition: Returns True when fm_agent/phases.json exists and
#     fm_agent/extracted_functions/ contains at least one spec-complete
#     extracted-function file per phase (scoped to submodules when provided).
#     Returns False otherwise.
# [SPLIT]
# extract_existing_specs(proj_dir) -> dict[str, {"spec": str, "info": str?}]
#   Pre-condition: fm_agent/extracted_functions/ exists and contains extracted
#     function files, some of which may have [SPEC] and [INFO] blocks
#   Post-condition: Returns a dict mapping each extracted-function relative path
#     to an object containing the text of its existing [SPEC] block and,
#     when present, its [INFO] block. Paths without [SPEC] blocks are omitted
#     from the returned dict.
# [SPLIT]
# _collect_changed_functions(proj_dir, old_commit_id, submodules=None)
#   -> dict[str, {"added": [str], "removed": [str], "modified": [str]}]
#   Pre-condition: proj_dir is a git repository containing old_commit_id;
#     submodules is None or a list of subdirectory names
#   Post-condition: Returns a dict keyed by source-file paths relative to
#     proj_dir. Each value contains lists of function names that were added,
#     removed, or modified between old_commit_id and the current working tree.
#     Source files with no function-level changes are omitted from the dict.
# [SPLIT]
# _remove_stale_extracted(proj_dir, modified_functions) -> None
#   Pre-condition: proj_dir is an absolute path to the project root and
#     fm_agent/extracted_functions/ and fm_agent/phases.json exist under it;
#     modified_functions is a dict whose keys are absolute source-file paths.
#   Post-condition: For every absolute source-file path that is a key in
#     modified_functions or listed in phases.json, the corresponding
#     extracted-function tree under fm_agent/extracted_functions/ is
#     reconciled with current codegraph output; any extracted function file
#     or directory that no longer corresponds to a current function is
#     deleted, empty parent directories pruned. Other extracted-function
#     files and directories are unchanged.
# [SPLIT]
# collect_relevent_function_scope(proj_dir, developer_intent,
#                                 changed_functions, range=None) -> list[str]
#   Pre-condition: developer_intent is a non-empty string describing a
#     modification goal; changed_functions maps source files to change sets
#   Post-condition: Returns a list of extracted-function relative paths
#     ordered by descending relevance to the developer intent, derived by
#     module-level, file-level, and function-level relevance scoring.
# [SPLIT]
# _update_specs_for_intent(proj_dir, work_dir, developer_intent,
#                          changed_functions, spec_files,
#                          extra_call_edges=None) -> list[str]
#   Pre-condition: developer_intent is a non-empty string; changed_functions
#     maps source files to their change sets; spec_files lists candidate
#     extracted-function relative paths
#   Post-condition: Returns a list of extracted-function relative paths whose
#     [SPEC] and/or [INFO] blocks were modified. For each function that is
#     either changed or present in spec_files, re-evaluates whether the
#     intended behavior spec needs updating; when a callee's spec is updated,
#     cascading [INFO] updates are applied to all callers of that callee.
# [SPLIT]
# _verify_incremental_functions(proj_dir, work_dir, changed_functions,
#                               updated_spec_files, submodules=None) -> list[str]
#   Pre-condition: updated_spec_files lists functions whose [SPEC] or [INFO]
#     blocks were modified in the spec-update stage
#   Post-condition: Returns a list of extracted-function relative paths where
#     the reasoner produced a MISMATCH verdict and bug validation confirmed the
#     violation. Verification scope is limited to: changed functions, functions
#     with updated specs, and functions that call a callee whose spec was
#     updated.
# [SPLIT]
# run_pipeline(proj_dir, domain_knowledge_files=None, submodules=None,
#              one_phase=False, extra_call_edges_path=None) -> None
#   Pre-condition: proj_dir is a valid directory containing source code
#   Post-condition: Executes the full 6-phase pipeline on proj_dir, producing
#     extracted functions, specs, verification results, and bug validation
#     reports under fm_agent/. Returns None.
# [INFO]

def run_incremental_pipeline(
    proj_dir,
    intent_file_path,
    old_commit_id,
    domain_knowledge_files=None,
    submodules=None,
    one_phase=False,
    extra_call_edges_path=None,
):
    """
    Run the pipeline in incremental mode, intent_file_path is a file (absolute path) defining the goal of modification.

    Returns the sorted list of verified files (paths relative to the extracted_functions
    dir) for which the reasoner reported a spec violation (MISMATCH) that bug validation
    then confirmed. The set of functions whose specs were updated is recorded to
    fm_agent/incremental_updated_specs.json as a side effect.
    """

    # run_pipeline and _run_setup_extract live in the top-level entry module (main.py);
    # import them lazily here to avoid a src -> main import cycle at module load time.
    from main import run_pipeline, _run_setup_extract

    work_dir = os.path.join(proj_dir, "fm_agent")
    script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    input_dir = os.path.join(work_dir, "extracted_functions")
    output_dir = os.path.join(work_dir, "logic_verification_results")
    extra_call_edges = load_call_edges(extra_call_edges_path)

    _setup_incremental_logging(work_dir)
    staged_knowledge = stage_domain_knowledge_files(
        proj_dir, work_dir, domain_knowledge_files
    )
    if staged_knowledge:
        logging.info(
            "  user domain knowledge: %d markdown file(s).",
            len(staged_knowledge),
        )

    logging.info("=" * 70)
    logging.info("INCREMENTAL PIPELINE START")
    logging.info("  project dir : %s", proj_dir)
    logging.info("  intent file : %s", intent_file_path)
    logging.info("  base commit : %s", old_commit_id)
    if submodules:
        logging.info("  submodule scope : %s", ", ".join(submodules))
    logging.info("=" * 70)

    # 1. Check whether there is a last run to compare against; if not, fall back to a full run since we have no basis for incremental analysis.
    logging.info("[Stage 1/10] Checking for a previous full run to compare against...")
    has_last_run = check_last_run_existence(proj_dir, submodules=submodules)
    if not has_last_run:
        logging.warning(
            "No previous full run detected (phases.json missing or incomplete extracted_functions), so falling back to a full run rather than incremental."
        )
        run_pipeline(
            proj_dir,
            domain_knowledge_files=domain_knowledge_files,
            submodules=submodules,
            one_phase=one_phase,
            extra_call_edges_path=extra_call_edges_path,
        )
        return
    logging.info("  -> previous full run found; proceeding with incremental analysis.")

    # 2. Check whether the intent file is valid; if not, fail since we don't know what to analyze incrementally.
    logging.info("[Stage 2/10] Loading developer intent...")
    developer_intent = ""
    if not os.path.isfile(intent_file_path):
        logging.error("Intent file %s does not exist; cannot run incremental pipeline.", intent_file_path)
        return
    else:
        with open(intent_file_path, "r") as f:
            developer_intent = f.read().strip()
        if not developer_intent:
            logging.error("Intent file %s is empty; cannot run incremental pipeline.", intent_file_path)
            return
    logging.info("  -> intent loaded (%d chars).", len(developer_intent))

    # Wipe the previous run's verification artifacts. The prior full run wrote a verdict for
    # EVERY function into logic_verification_results/ and every confirmed bug into
    # bug_validation/, but this incremental run only re-verifies the changed/affected subset.
    # If left in place, those folders would mix stale full-run results with this run's fresh
    # ones, making it ambiguous which verdicts are the latest. Clear them so the folders hold
    # only this incremental run's output.
    for stale_dir in (output_dir, os.path.join(work_dir, "bug_validation")):
        if os.path.isdir(stale_dir):
            shutil.rmtree(stale_dir, ignore_errors=True)
            logging.info("  -> removed stale results dir %s.", stale_dir)

    # Also remove the scope-selection and spec-update prompt/result artifacts a prior
    # incremental run left directly in fm_agent/ (module/file relevance selection and
    # per-function spec updates). They are keyed by a per-run index, so leftovers from an
    # earlier run would sit alongside this run's and obscure which artifacts are current.
    stale_artifact_globs = (
        "select_relevant_modules.md", "relevant_modules.json",
        "select_relevant_files_*.md", "relevant_files_*.json",
        "spec_update_*.md", "spec_update_*.json",
    )
    removed_artifacts = 0
    for pattern in stale_artifact_globs:
        for stale_file in glob.glob(os.path.join(work_dir, pattern)):
            try:
                os.remove(stale_file)
                removed_artifacts += 1
            except OSError:
                pass
    if removed_artifacts:
        logging.info("  -> removed %d stale scope-selection artifact(s) from %s.", removed_artifacts, work_dir)

    # 3. Re-generate the phases.json
    logging.info("[Stage 3/10] Generating new phases.json based on current working tree...")
    _run_setup_extract(
        proj_dir, work_dir, script_dir,
        is_incremental=True, submodules=submodules,
        one_phase=one_phase,
    )
    logging.info("  -> phases.json regenerated.")

    # 4. Update functions under fm_agent/extracted_functions/.
    #    Capture the previous run's specs first (re-extraction overwrites each file with
    #    the raw source for the current code), then re-extract, then restore the captured
    #    [SPEC]/[INFO] headers onto every function that still exists. Functions that were
    #    added or whose extraction path changed are left unspecced for the spec-update
    #    stage to handle; unchanged functions keep their previous specs verbatim.
    logging.info("[Stage 4/10] Re-extracting functions and restoring previous specs...")
    old_spec = extract_existing_specs(proj_dir)
    logging.info("  -> captured %d existing spec block(s) before re-extraction.", len(old_spec))
    # Rebuild the codegraph index before re-extraction. The index still reflects the code as
    # of the previous full run, but the working tree has changed since then; run_extraction
    # (and the downstream scope ranking) read function bodies and spans from codegraph, so a
    # stale index would yield boundaries for the old code. try_codegraph_init rebuilds by
    # default; no-op when codegraph is uninstalled (extraction then falls back to regex).
    try_codegraph_init(proj_dir)
    run_extraction(proj_dir, work_dir=work_dir, force=True, verbose=True)
    _reapply_existing_specs(proj_dir, old_spec)
    logging.info("  -> functions re-extracted and prior [SPEC]/[INFO] headers reapplied.")

    # 5. Collect changed functions by comparing against the old version of functions in commit_id
    logging.info("[Stage 5/10] Collecting changed functions vs. base commit...")
    changed_functions = _collect_changed_functions(
        proj_dir, old_commit_id, submodules=submodules
    )
    n_added = sum(len(c.get("added", [])) for c in changed_functions.values())
    n_removed = sum(len(c.get("removed", [])) for c in changed_functions.values())
    n_modified = sum(len(c.get("modified", [])) for c in changed_functions.values())
    logging.info(
        "  -> %d changed file(s): %d added, %d modified, %d removed function(s).",
        len(changed_functions), n_added, n_modified, n_removed,
    )

    # 5b. Delete extracted-function files for functions (or whole source files) that were
    #     removed since old_commit_id. Re-extraction never rewrites these, so without this
    #     they linger as stale specs and would pollute the file list and call graph below.
    _remove_stale_extracted(proj_dir, changed_functions)
    logging.info("  -> stale extracted-function files for removed functions deleted.")

    # 6. Update file list
    logging.info("[Stage 6/10] Collecting file list...")
    file_list_path = os.path.join(work_dir, "fm_agent_file_list.json")
    file_list = collect_file_names(input_dir, file_list_path)
    if submodules:
        with open(os.path.join(work_dir, "phases.json"), "r") as f:
            phases_data = json.load(f)
        file_list = _write_file_names(
            _get_all_phase_files(phases_data, input_dir), file_list_path
        )
    logging.info("  -> file list has %d entr(ies).", len(file_list))

    # 7. Update top-down layers
    logging.info("[Stage 7/10] Generating topdown layers...")
    with open(os.path.join(work_dir, "phases.json"), "r") as f:
        phases_data = json.load(f)
    generate_topdown_layers(work_dir, extra_call_edges=extra_call_edges)
    logging.info("  -> topdown layers generated for %d phase(s).", len(phases_data.get("phases", [])))

    # 8. Collect the scope of functions relevant to the developer intent (the intent file defines the goal of modification).
    logging.info("[Stage 8/10] Collecting functions relevant to the developer intent...")
    spec_files = collect_relevent_function_scope(proj_dir, developer_intent, changed_functions)
    logging.info("  -> %d function(s) judged relevant to the intent.", len(spec_files))

    # 9. Re-generate the spec of functions if it satisfies one of the following conditions: 1) the function is changed; 2) the function is relevant to the developer intent.
    logging.info("[Stage 9/10] Updating specs for changed and relevant functions...")
    updated_spec_files = _update_specs_for_intent(
        proj_dir,
        work_dir,
        developer_intent,
        changed_functions,
        spec_files,
        extra_call_edges=extra_call_edges,
    )
    record_path = os.path.join(work_dir, "incremental_updated_specs.json")
    with open(record_path, "w") as f:
        json.dump({"updated_specs": updated_spec_files}, f, indent=2)
    logging.info(
        "  -> %d spec(s) updated; record written to %s.",
        len(updated_spec_files), record_path,
    )

    # 10. Run the verification stage only on the functions that satisfy one of the following conditions: 1) the function is changed; 2) the function spec is changed after step 9; 3) the callee spec of the function is changed.
    logging.info("[Stage 10/10] Verifying changed and affected functions...")
    buggy_files = _verify_incremental_functions(
        proj_dir, work_dir, changed_functions, updated_spec_files,
        submodules=submodules,
    )
    logging.info("=" * 70)
    logging.info(
        "INCREMENTAL PIPELINE DONE: bug validation confirmed bugs in %d function(s).",
        len(buggy_files),
    )
    for bf in buggy_files:
        logging.info("  - %s", bf)
    logging.info("=" * 70)
    return buggy_files

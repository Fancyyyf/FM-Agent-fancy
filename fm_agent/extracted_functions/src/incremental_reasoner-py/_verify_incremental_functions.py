# [SPEC]
# Unit: src/incremental_reasoner.py
#
# _verify_incremental_functions(proj_dir, work_dir, changed_functions,
#                                updated_spec_files, submodules=None)
#   -> list[str]
#
# Pre-condition:
#   - proj_dir is a path to an existing directory under version control.
#   - work_dir is a writable directory whose subdirectory
#     extracted_functions/ contains per-function extracted source files
#     (possibly with [SPEC] blocks) and whose subdirectories
#     logic_verification_results/ and bug_validation/ exist and are writable.
#   - changed_functions is a dict mapping absolute source-file paths to dicts
#     with keys "added", "modified", "removed", each mapping to a list of
#     function names.
#   - updated_spec_files is a list of extracted-function relative paths (from
#     work_dir/extracted_functions/) whose [SPEC] or [INFO] blocks were
#     modified in the spec-update stage.
#   - submodules, when not None, is a list of relative directory paths within
#     proj_dir.
#
# Post-condition:
#   - Returns a sorted list of extracted-function relative paths for which the
#     reasoner produced a MISMATCH verdict and bug validation subsequently
#     confirmed the violation (confirmation_status equal to "confirmed").
#   - The set of functions verified is the union of:
#       a) Functions whose extracted files exist under work_dir and whose
#          names appear in changed_functions entries with status "added" or
#          "modified".
#       b) Functions whose extracted files exist under work_dir and whose
#          relative paths appear in updated_spec_files.
#     A function satisfying both conditions is verified once.
#   - When submodules is not None, a function is verified only if its
#     extracted relative path (with "/" separators) starts with one of the
#     submodule paths.
#   - When the resulting verification set is empty, returns an empty list
#     without invoking the reasoner or bug validation.
#   - Before reasoning begins, every pre-existing verification result file
#     under work_dir/logic_verification_results/ corresponding to a function
#     in the verification set is removed, so the reasoner produces a fresh
#     verdict against the current code and (possibly updated) spec.
#   - Every function in the verification set is submitted to the reasoner.
#     Functions whose verification raises an exception do not contribute to
#     the MISMATCH collection and do not prevent other functions from being
#     verified.
#   - Every function that receives a MISMATCH verdict is submitted to bug
#     validation. Functions whose bug validation raises an exception do not
#     contribute to the confirmed-bug collection and do not prevent other
#     functions from being validated.
#   - A bug_validation/summary.json file is written to work_dir aggregating
#     the confirmation status of all submitted bug validations, regardless of
#     whether any bugs were confirmed.
#   - The returned list is empty when no confirmed bugs exist.
#   - Does not modify any file outside of work_dir/.
# [SPEC]

# [INFO]
# _modified_function_targets(proj_dir, changed_functions, classes=(...))
#   -> dict
#   Pre-condition: changed_functions maps source-file paths to status dicts
#     with keys "added", "modified", "removed". classes is a tuple of status
#     names to include.
#   Post-condition: Returns a dict whose values are absolute paths to
#     extracted-function files for functions whose status matches one of the
#     given classes.
# [SPLIT]
# _is_under_submodules(rel, submodules) -> bool
#   Pre-condition: rel is a relative path string with "/" separators.
#     submodules is a list of directory path strings.
#   Post-condition: Returns True when rel starts with any path in
#     submodules, False otherwise.
# [SPLIT]
# _verify_single_file(fpath, extracted_dir, output_dir, language, work_dir=...)
#   -> (str, str)
#   Pre-condition: fpath is an absolute path to an extracted-function file
#     that may contain a [SPEC] block. extracted_dir is the root of the
#     extracted-functions tree. output_dir is a writable directory for
#     verification results.
#   Post-condition: Runs the reasoner on the function at fpath and writes
#     the verdict JSON to output_dir at a mirrored relative path. Returns a
#     tuple of (relative path from extracted_dir, verdict) where verdict is
#     one of "MATCH", "MISMATCH", "ERROR", or "SKIPPED".
# [SPLIT]
# _validate_single_bug(result_json_rel, proj_dir, work_dir) -> None
#   Pre-condition: result_json_rel is a path (relative to proj_dir) to a
#     reasoner result JSON file whose verdict is "MISMATCH".
#   Post-condition: Runs bug validation via opencode on the MISMATCH result
#     and writes the validation outcome to
#     work_dir/bug_validation/<bug_id>.result.json, where bug_id is derived
#     by replacing path separators in the result-relative path with "--".
# [SPLIT]
# _generate_validation_summary(work_dir) -> None
#   Pre-condition: work_dir/bug_validation/ contains zero or more
#     <bug_id>.result.json files, each with a confirmation_status field.
#   Post-condition: Writes work_dir/bug_validation/summary.json aggregating
#     the count of total, confirmed, not-confirmed, and error-validation
#     results across all result files present.
# [INFO]

def _verify_incremental_functions(
    proj_dir, work_dir, changed_functions, updated_spec_files, submodules=None
):
    """
    Step 10: re-run the verification stage (reasoner + bug validation) on only the functions
    whose implementation-vs-spec verdict may have drifted because of this modification.

    A function is verified when it satisfies at least one of:
      1) it was changed in the working tree (added or modified), or
      2) its own [SPEC] or [INFO] block was updated in step 9.

    Note on callees: a function whose callee's [SPEC] changed needs re-verification ONLY if
    that change forced its own [INFO] block (the callee contract it reasons against) to be
    updated. Step 9's upward reconciliation already rewrites exactly those callers' [INFO]
    blocks and includes them in updated_spec_files, so condition (2) covers them — a caller
    whose [INFO] did not need to change is left alone and is correctly NOT re-verified.

    Each target is verified by invoking the reasoner (src/reasoner.py, via the per-file
    wrapper verification._verify_single_file, which calls reasoner() and writes the result
    JSON) — not the streaming watcher. The stale verification result of every target is
    removed first so the reasoner re-runs against the current implementation and (possibly
    updated) spec rather than reusing the cached verdict from the previous full run.

    A reasoner MISMATCH is only a candidate bug; each one is then handed to bug validation
    (verification._validate_single_bug, an opencode pass) which confirms or rejects it.

    Returns the sorted list of extracted-function files (paths relative to the
    extracted_functions dir) whose reasoner MISMATCH was confirmed a bug by bug validation.
    """
    extracted_dir = os.path.join(work_dir, "extracted_functions")
    output_dir = os.path.join(work_dir, "logic_verification_results")

    verify_targets = set()  # absolute extracted-function paths

    # (1) Functions changed in the working tree (added/modified; removed ones are gone).
    verify_targets.update(
        _modified_function_targets(
            proj_dir, changed_functions, classes=("added", "modified")
        ).values()
    )

    # (2) Functions whose [SPEC] or [INFO] block was updated in step 9 (updated_spec_files
    #     already includes both functions whose own spec changed and callers whose [INFO]
    #     was reconciled against an updated callee).
    for rel in updated_spec_files:
        verify_targets.add(os.path.join(extracted_dir, rel))

    # Keep only functions that still exist on disk; the reasoner reads these extracted files
    # directly and skips any without a [SPEC] block.
    file_list = sorted({
        os.path.relpath(path, extracted_dir)
        for path in verify_targets
        if os.path.exists(path)
    })
    if submodules:
        file_list = [
            rel for rel in file_list
            if _is_under_submodules(rel.replace(os.sep, "/"), submodules)
        ]
    if not file_list:
        logging.info("    [verify] no functions require re-verification.")
        return []
    logging.info("    [verify] running reasoner on %d function(s)...", len(file_list))

    # Drop stale verification results so the reasoner re-runs rather than reusing the cached
    # verdict from the previous full run.
    for rel in file_list:
        stale = os.path.join(output_dir, os.path.splitext(rel)[0] + ".json")
        if os.path.exists(stale):
            os.remove(stale)

    # Verify every target by invoking the reasoner (via _verify_single_file). The reasoner
    # makes LLM calls, so run the targets concurrently like the full run does, bounded by
    # MAX_WORKERS. _verify_single_file writes each verdict to output_dir and returns it.
    mismatches = []

    def _verify(rel):
        fpath = os.path.join(extracted_dir, rel)
        language = _VERIFY_EXT_TO_LANG.get(os.path.splitext(fpath)[1], "C")
        _, verdict = _verify_single_file(fpath, extracted_dir, output_dir, language, work_dir=work_dir)
        return rel, verdict

    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(_verify, rel): rel for rel in file_list}
        for future in concurrent.futures.as_completed(futures):
            rel = futures[future]
            try:
                _, verdict = future.result()
            except Exception:
                logging.exception("Verification failed for %s", rel)
                continue
            if verdict == "MISMATCH":
                mismatches.append(rel)

    logging.info("    [verify] reasoner reported %d MISMATCH(es) (candidate bugs).", len(mismatches))
    if not mismatches:
        return []

    # Bug validation: the reasoner's MISMATCH is only a candidate bug, so validate each one
    # with opencode (_validate_single_bug writes work_dir/bug_validation/<bug_id>.result.json
    # with a confirmation_status). Run them concurrently, bounded by MAX_WORKERS.
    logging.info("    [verify] validating %d candidate bug(s) with opencode...", len(mismatches))

    def _validate(rel):
        result_json_rel = os.path.join(
            os.path.relpath(output_dir, proj_dir),
            os.path.splitext(rel)[0] + ".json",
        )
        _validate_single_bug(result_json_rel, proj_dir, work_dir)
        return rel

    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(_validate, rel): rel for rel in mismatches}
        for future in concurrent.futures.as_completed(futures):
            rel = futures[future]
            try:
                future.result()
            except Exception:
                logging.exception("Bug validation failed for %s", rel)

    # Summarize all validation results into work_dir/bug_validation/summary.json, like run_pipeline.
    _generate_validation_summary(work_dir)

    # Collect the MISMATCHes that bug validation confirmed as real bugs. bug_id is the
    # result-relative path with separators replaced by "--".
    bug_validation_dir = os.path.join(work_dir, "bug_validation")
    confirmed = []
    for rel in mismatches:
        bug_id = os.path.splitext(rel)[0].replace(os.sep, "--").replace("/", "--")
        result_path = os.path.join(bug_validation_dir, f"{bug_id}.result.json")
        if not os.path.exists(result_path):
            continue
        try:
            with open(result_path) as rf:
                data = json.load(rf)
        except (ValueError, OSError):
            continue
        if data.get("confirmation_status") == "confirmed":
            confirmed.append(rel)

    return sorted(confirmed)

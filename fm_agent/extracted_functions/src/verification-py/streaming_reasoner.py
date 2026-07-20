# [SPEC]
# Unit: src/verification-py/streaming_reasoner.py
#
# streaming_reasoner(input_dir, output_dir, file_list=None, proj_dir=None, work_dir=None, poll_interval=2, spec_procs=None, already_processed=None, resume=False) -> set
#
# Pre-condition:
#   - input_dir is a directory path containing extracted function files, where each
#     file is expected to eventually have [SPEC]/[INFO] blocks prepended
#   - output_dir is a writable directory path to store verification result JSON files
#   - file_list, if provided, is a collection of relative file paths; each path ends
#     with an extension in EXT_TO_LANG
#   - proj_dir, if provided, is the project root directory path
#   - work_dir defaults to proj_dir when omitted and proj_dir is not None
#   - poll_interval is a positive number of seconds
#   - spec_procs, if provided, is a collection of handles representing in-progress
#     specification-generation processes (Popen or Future instances)
#   - already_processed, if provided, is a collection of file paths already verified
#   - resume is a boolean indicating whether to skip already-verified files
#
# Post-condition:
#   - Every file in input_dir (scoped to file_list when provided) whose is_file_ready()
#     returns True will be submitted to _verify_single_file exactly once; a readied
#     file that was in already_processed is NOT resubmitted
#   - A verification result JSON is written to output_dir for every submitted file,
#     mirroring the relative path structure of input_dir; the verdict field in each
#     result is one of: "MATCH", "MISMATCH", "ERROR", "SKIPPED"
#   - For every verified file whose verdict is "MISMATCH" and proj_dir is not None,
#     a bug-validation task is submitted via _validate_single_bug; the validation
#     writes a result JSON at proj_dir/bug_validation/<bug_id>.result.json where
#     bug_id is derived from the result JSON path by stripping the
#     fm_agent/logic_verification_results/ prefix, removing ".json", and replacing
#     "/" with "--"
#   - Progress output is printed for each completed verification: MATCH and SKIPPED
#     files are marked with a green check, confirmed bugs with a red cross; each
#     line is prefixed with "[<N>/<total>] <relative_path>: <label>"
#   - When all expected files have been verified, all reasoning futures are done,
#     and no validation futures remain in-flight, the loop exits normally
#   - When spec_procs is provided and every process has exited via _spec_task_done,
#     and not all expected files are ready: the function exits with a warning.
#     If no files received specs at all, the warning states no [SPEC]/[INFO] markers
#     were observed; otherwise it reports how many files are missing specs and
#     lists each as "[pending]"
#   - On KeyboardInterrupt: all in-flight reasoning and validation futures are
#     waited on to completion before the function returns
#   - If proj_dir is not None, _generate_validation_summary is called after all
#     processing ends (normal exit, early-exit on stalled specs, or interrupt),
#     producing proj_dir/bug_validation/summary.json
#   - Returns a set of file paths (absolute paths within input_dir) that were
#     successfully verified; this set is a superset of already_processed when
#     already_processed is provided
#   - The returned set is the same object as the already_processed set when
#     already_processed was provided (not a copy)
# [SPEC]

# [INFO]
# is_file_ready(file_path) -> bool
#   Pre-condition: file_path is a valid path to an extracted function file
#   Post-condition: Returns True iff the file content contains two or more
#     "[SPEC]" markers AND two or more "[INFO]" markers
# [SPLIT]
# _verify_single_file(file_path, input_dir, output_dir, language, work_dir, resume) -> (file_path, verdict)
#   Pre-condition: file_path is a ready extracted function file; language is one of
#     the language labels from EXT_TO_LANG; output_dir exists and is writable
#   Post-condition: Returns a (file_path, verdict) tuple where verdict is "MATCH",
#     "MISMATCH", "ERROR", or "SKIPPED"; writes a verification result JSON to
#     output_dir at a path mirroring file_path relative to input_dir, with the
#     extension changed to ".json". On resume, if a valid result JSON already
#     exists at the output path, returns its verdict without re-running reasoning.
# [SPLIT]
# _validate_single_bug(result_json_rel, proj_dir, work_dir, resume) -> None
#   Pre-condition: result_json_rel is a relative path to a MISMATCH result JSON
#     file under output_dir; proj_dir is the project root
#   Post-condition: Writes a bug report (.md) and a validation result JSON
#     (.result.json) to proj_dir/bug_validation/, where the bug_id is derived
#     from the result JSON path; the result JSON contains a confirmation_status
#     field of "confirmed", "not_confirmed", or "error". On resume, if the
#     .result.json already exists, skips re-validation.
# [SPLIT]
# _generate_validation_summary(work_dir) -> None
#   Pre-condition: work_dir is a directory that may contain a bug_validation/
#     subdirectory with .result.json files
#   Post-condition: Writes bug_validation/summary.json under work_dir containing
#     total_reported, total_confirmed, total_not_confirmed, total_error counts and
#     a bugs array of per-bug objects; confirmed bugs are listed first, then
#     not_confirmed, then error, each group sorted alphabetically by id
# [SPLIT]
# _spec_task_done(p) -> bool
#   Pre-condition: p is a subprocess.Popen handle or a concurrent.futures.Future
#   Post-condition: Returns True if the represented task or process has completed
#     execution; False otherwise
# [SPLIT]
# _spec_task_exit_code(p) -> int | None
#   Pre-condition: _spec_task_done(p) returned True
#   Post-condition: Returns the integer exit code of the completed process or
#     task, or None if no exit code is available
# [INFO]

def streaming_reasoner(input_dir, output_dir, file_list=None, proj_dir=None, work_dir=None, poll_interval=2, spec_procs=None, already_processed=None, resume=False):
    """Continuously watch input_dir for ready files, verify them, and validate bugs."""
    if work_dir is None:
        work_dir = proj_dir
    os.makedirs(output_dir, exist_ok=True)
    processed = set(already_processed) if already_processed else set()

    # Build the set of expected files from file_list (only code files)
    if file_list is not None:
        expected_files = set(
            os.path.join(input_dir, rel) for rel in file_list
            if os.path.splitext(rel)[1] in EXT_TO_LANG
        )
    else:
        expected_files = None

    import concurrent.futures

    # Count files that still need verification in this watcher invocation.
    if expected_files is not None:
        total_expected = len(expected_files)
        pending_expected = expected_files - processed
        num_functions = len(pending_expected)
        if num_functions == total_expected:
            print(f"Functions pending verification: {num_functions}")
        else:
            print(f"Functions pending verification: {num_functions} of {total_expected}")
    else:
        num_functions = sum(
            1 for root, _, files in os.walk(input_dir)
            for fname in files
            if os.path.splitext(fname)[1] in EXT_TO_LANG
        )
        print(f"Functions pending verification: {num_functions}")

    logging.info(f"Watching {input_dir} for ready files (poll every {poll_interval}s)...")
    completed_count = 0

    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            reasoning_futures = {}
            validation_futures = {}
            submitted = set()

            while True:
                # Scan for new ready files
                for root, _, files in os.walk(input_dir):
                    for fname in files:
                        ext = os.path.splitext(fname)[1]
                        if ext not in EXT_TO_LANG:
                            continue
                        file_path = os.path.join(root, fname)
                        if expected_files is not None and file_path not in expected_files:
                            continue
                        if file_path in processed:
                            continue
                        if file_path in submitted:
                            continue
                        if not is_file_ready(file_path):
                            continue

                        # File is ready and not yet submitted or processed.
                        submitted.add(file_path)
                        language = EXT_TO_LANG.get(ext, "C")
                        future = executor.submit(
                            _verify_single_file, file_path, input_dir, output_dir, language, work_dir, resume
                        )
                        reasoning_futures[future] = file_path
                        logging.info(f"Submitted: {file_path}")

                # Collect completed reasoning futures (non-blocking)
                done = [f for f in reasoning_futures if f.done()]
                for future in done:
                    fpath = reasoning_futures.pop(future)
                    submitted.discard(fpath)
                    try:
                        _, verdict = future.result()
                        processed.add(fpath)
                        completed_count += 1
                        rel_path = os.path.relpath(fpath, proj_dir) if proj_dir else os.path.relpath(fpath, input_dir)
                        # Submit bug validation for MISMATCH results; defer printing
                        if verdict == "MISMATCH" and proj_dir is not None:
                            rel = os.path.relpath(fpath, input_dir)
                            result_json_rel = os.path.join(
                                os.path.relpath(output_dir, proj_dir),
                                os.path.splitext(rel)[0] + ".json",
                            )
                            vf = executor.submit(
                                _validate_single_bug, result_json_rel, proj_dir, work_dir, resume
                            )
                            validation_futures[vf] = (fpath, rel_path, result_json_rel, completed_count)
                            logging.info(f"Submitted validation: {fpath}")
                        else:
                            if verdict == "MATCH" or verdict == "SKIPPED":
                                label = "\033[32m✔\033[0m"
                                if verdict == "SKIPPED":
                                    label += " (no spec)"
                            else:
                                label = verdict
                            print(f"[{completed_count}/{num_functions}] {rel_path}: {label}")
                    except Exception as exc:
                        logging.error(f"Error verifying {fpath}: {exc}")

                # Collect completed validation futures (non-blocking)
                val_done = [f for f in validation_futures if f.done()]
                for future in val_done:
                    fpath, rel_path, result_json_rel, count = validation_futures.pop(future)
                    try:
                        future.result()
                        # Read validation result to check confirmation
                        parts = result_json_rel
                        prefix = os.path.join("fm_agent", "logic_verification_results") + os.sep
                        if parts.startswith(prefix):
                            parts = parts[len(prefix):]
                        elif parts.startswith("fm_agent/logic_verification_results/"):
                            parts = parts[len("fm_agent/logic_verification_results/"):]
                        bug_id = os.path.splitext(parts)[0].replace(os.sep, "--").replace("/", "--")
                        result_path = os.path.join(work_dir, "bug_validation", f"{bug_id}.result.json")
                        confirmed = False
                        if os.path.exists(result_path):
                            with open(result_path) as rf:
                                result_data = json.load(rf)
                            confirmed = result_data.get("confirmation_status") == "confirmed"
                        if confirmed:
                            print(f"[{count}/{num_functions}] {rel_path}: \033[31m✘\033[0m")
                        else:
                            print(f"[{count}/{num_functions}] {rel_path}: \033[32m✔\033[0m")
                        logging.info(f"Validation completed: {fpath} (confirmed={confirmed})")
                    except Exception as exc:
                        logging.error(f"Validation error for {fpath}: {exc}")

                # Check if all expected files have been processed
                all_reasoning_done = (
                    expected_files is not None
                    and processed >= expected_files
                    and not reasoning_futures
                )
                if all_reasoning_done and not validation_futures:
                    logging.info("All files verified and validated. Done.")
                    break

                # Detect if spec generation subprocesses exited before all files are ready
                _all_procs = spec_procs if spec_procs else None
                if _all_procs is not None and all(_spec_task_done(p) for p in _all_procs):
                    unready = (expected_files or set()) - processed
                    if unready and not reasoning_futures and not validation_futures:
                        exit_codes = [_spec_task_exit_code(p) for p in _all_procs]
                        if not processed:
                            # No function got a spec at all – this is an error
                            logging.warning(
                                f"Spec generation process(es) exited (codes {exit_codes}) "
                                f"but no files received [SPEC]/[INFO] markers."
                            )
                        else:
                            # Some functions are missing specs; leave them pending for retry.
                            logging.warning(
                                f"Spec generation process(es) exited (codes {exit_codes}), "
                                f"{len(unready)} files missing specs, leaving them pending for retry."
                            )
                            for uf in sorted(unready):
                                rel_path = os.path.relpath(uf, proj_dir) if proj_dir else os.path.relpath(uf, input_dir)
                                print(f"[pending] {rel_path}: no spec yet; will retry")
                        break

                time.sleep(poll_interval)

    except KeyboardInterrupt:
        logging.info("Stopping watcher...")
        # Wait for in-flight tasks
        all_futures = {}
        all_futures.update(reasoning_futures)
        all_futures.update(validation_futures)
        for future in all_futures:
            fpath = all_futures[future]
            try:
                future.result()
                logging.info(f"Completed: {fpath}")
            except Exception as exc:
                logging.error(f"Error for {fpath}: {exc}")
        logging.info("Done.")

    # Generate validation summary after all work is done
    if proj_dir is not None:
        _generate_validation_summary(work_dir)

    return processed

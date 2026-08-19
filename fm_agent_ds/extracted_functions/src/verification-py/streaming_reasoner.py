def streaming_reasoner(
    input_dir,
    output_dir,
    file_list=None,
    proj_dir=None,
    work_dir=None,
    poll_interval=2,
    spec_procs=None,
    already_processed=None,
    resume=False,
    bug_validator_path=None,
):
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
                                _validate_single_bug,
                                result_json_rel,
                                proj_dir,
                                work_dir,
                                resume=resume,
                                bug_validator_path=bug_validator_path,
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
                                f"but no .spec.json/.info.json sidecar pairs were created."
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

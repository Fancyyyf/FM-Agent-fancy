def _update_specs_for_intent(
    proj_dir,
    work_dir,
    developer_intent,
    changed_functions,
    relevant_rel_files,
    extra_call_edges=None,
):
    """
    re-generate the [SPEC] (and dependent [INFO]) blocks of every function that is
    either changed or relevant to the developer intent, propagating to callees.

    Seeds from the changed functions (added/modified) and the relevant extracted-function
    files returned by collect_relevent_function_scope, then processes functions in top-down
    order (callers before callees). For each function, opencode reads its current [SPEC]
    block and decides whether it must change to reflect developer_intent. A function with no
    existing [SPEC] block (e.g. one freshly added by the modification) instead has a spec
    generated from scratch the way the full run does. If a spec is written or generated, the
    new [SPEC] is written back (source untouched), and then:

      - Downward: opencode decides whether the function's own [INFO] block (the expected
        specs of its callees) must change too, and any callee whose expected spec changed is
        queued to have its own spec file re-checked.
      - Upward: every caller's [INFO] block (which records this function as one of its
        callees) is reconciled with the function's new [SPEC] so the two do not conflict
        (they need not be identical).

    Returns the sorted list of extracted-function files (paths relative to the
    extracted_functions dir) whose [SPEC]/[INFO] block was changed.
    """
    extracted_dir = os.path.join(work_dir, "extracted_functions")

    callees_map, callers_map, file_map, edge_aliases_map = _project_call_graph(
        work_dir,
        extra_call_edges=extra_call_edges,
    )

    # Seed: functions changed in the working tree (added/modified — removed ones no longer
    # exist on disk) plus functions relevant to the developer intent.
    seed = set()
    changed_targets = _modified_function_targets(
        proj_dir, changed_functions, classes=("added", "modified")
    )
    seed.update(changed_targets.keys())
    for rel in relevant_rel_files:
        seed.add(_file_to_fqn(os.path.join(extracted_dir, rel), work_dir))

    if not seed:
        logging.info("    [specs] no changed or relevant functions to update; skipping.")
        return []
    logging.info(
        "    [specs] seeded %d function(s) for spec re-generation (%d changed, %d relevant).",
        len(seed), len(changed_targets), len(relevant_rel_files),
    )

    # Top-down order (callers before the callees they depend on); FQNs absent from the layer
    # graph sort last, by name.
    topdown = _topdown_ordered_fqns(work_dir, extra_call_edges=extra_call_edges)
    order_index = {fqn: i for i, fqn in enumerate(topdown)}

    def _order_key(fqn):
        return (order_index.get(fqn, len(order_index)), fqn)

    def _plan_spec_update(fqn, idx):
        """
        Decide fqn's new [SPEC]/[INFO] and return an apply-plan, or None to skip.

        Makes the opencode LLM call (the slow part) but performs NO file writes, so a batch of
        mutually independent functions can run this concurrently. The returned plan carries the
        exact file content to write plus what the serial apply phase needs for downward
        propagation; None means the function does not exist, is an unsupported language, or its
        spec did not change.
        """
        fpath = file_map.get(fqn)
        if not fpath or not os.path.isfile(fpath):
            return None
        ext = fpath.rsplit(".", 1)[-1] if "." in os.path.basename(fpath) else ""
        lang_key = EXT_TO_LANG.get(ext)
        if not lang_key:
            return None
        lang_cfg = LANG_CONFIG[lang_key]
        comment_prefix = lang_cfg["comment_prefix"]
        spec_marker = lang_cfg["spec_marker"]

        with open(fpath, "r", errors="replace") as f:
            content = f.read()
        leading = _extract_leading_spec_comments(content, comment_prefix, spec_marker)
        callee_names = sorted({c.split("::")[-1] for c in callees_map.get(fqn, ())})

        if leading is None:
            # No existing specification (e.g. a freshly added, unspecced function) — generate
            # one from scratch the way the full run does, rather than skipping the function.
            source = content
            old_spec, old_info = None, None
            caller_context = _collect_caller_context(
                fqn, callers_map, file_map, edge_aliases_map
            )
            result = _opencode_generate_spec(
                proj_dir, work_dir, idx, fqn, lang_key, comment_prefix,
                developer_intent, callee_names, source, caller_context,
            )
        else:
            source = content[len(leading):]
            old_spec, old_info = _split_spec_and_info(leading, comment_prefix, spec_marker)
            result = _llm_check_spec_update(
                proj_dir, work_dir, idx, fqn, lang_key, comment_prefix,
                developer_intent, old_spec, old_info, callee_names, source,
            )

        if not result or not result.get("spec_updated"):
            return None
        new_spec = (result.get("new_spec") or "").strip()
        if not new_spec:
            return None

        if leading is None:
            # Freshly generated: take the [INFO] block opencode produced (if any). Treat it as
            # "updated" so its recorded callee expectations propagate downward below.
            new_info = (result.get("new_info") or "").strip()
            info_block = new_info or None
            info_updated = bool(new_info)
        else:
            # Keep the existing [INFO] block unless opencode rewrote it. A modified function may
            # now call a different set of callees, so a fresh [INFO] block can legitimately be
            # created even when the function previously had none (old_info is None) — gate on
            # whether opencode produced a block, not on a prior block existing.
            info_block = old_info
            info_updated = False
            if result.get("info_updated"):
                new_info = (result.get("new_info") or "").strip()
                if new_info:
                    info_block = new_info
                    info_updated = True

        # Splice the new block(s) back in, leaving the function source unchanged (mirrors the
        # full run's specced-file layout: [SPEC], blank line, optional [INFO], blank line, source).
        new_block = new_spec.rstrip("\n")
        if info_block is not None:
            new_block += "\n\n" + info_block.strip("\n")

        return {
            "fqn": fqn,
            "fpath": fpath,
            "write_content": new_block + "\n\n" + source.lstrip("\n"),
            "new_spec": new_spec,
            "info_updated": info_updated,
            "updated_callees": result.get("updated_callees") or [],
        }

    def _reconcile_caller(caller_fqn, updates, base_idx):
        """
        Reconcile caller_fqn's [INFO] block against a sequence of changed callees.

        updates is a list of (callee_name, callee_new_spec). The entries are applied
        sequentially, re-reading the caller file between each, because they all edit the same
        file — so a single caller is one unit of work and DIFFERENT callers run concurrently
        (see the batch loop). base_idx + offset gives each opencode call a unique artifact name.
        Returns the caller's path if any reconciliation changed it, else None.
        """
        cpath = file_map.get(caller_fqn)
        if not cpath or not os.path.isfile(cpath):
            return None
        cext = cpath.rsplit(".", 1)[-1] if "." in os.path.basename(cpath) else ""
        clang = EXT_TO_LANG.get(cext)
        if not clang:
            return None
        ccfg = LANG_CONFIG[clang]
        cprefix = ccfg["comment_prefix"]
        cmarker = ccfg["spec_marker"]

        changed = False
        for offset, (callee_name, callee_new_spec) in enumerate(updates):
            with open(cpath, "r", errors="replace") as f:
                ccontent = f.read()
            cleading = _extract_leading_spec_comments(ccontent, cprefix, cmarker)
            if cleading is None:
                continue
            csource = ccontent[len(cleading):]
            c_spec, c_info = _split_spec_and_info(cleading, cprefix, cmarker)
            if c_info is None:
                # No callee-contract block to reconcile.
                continue

            cresult = _llm_check_caller_info_update(
                proj_dir, work_dir, base_idx + offset, caller_fqn, callee_name, clang, cprefix,
                callee_new_spec, c_info, csource,
            )
            if not cresult or not cresult.get("info_updated"):
                continue
            c_new_info = (cresult.get("new_info") or "").strip()
            if not c_new_info:
                continue

            c_block = c_spec.rstrip("\n") + "\n\n" + c_new_info.strip("\n")
            with open(cpath, "w") as f:
                f.write(c_block + "\n\n" + csource.lstrip("\n"))
            changed = True
        return cpath if changed else None

    checked = set()
    to_check = set(seed)
    changed_spec_files = set()
    counter = 0
    round_num = 0

    # Process the pending frontier in rounds. Each round takes the maximal set of mutually
    # independent functions — those with no still-pending caller, i.e. the roots of the current
    # frontier — and runs them concurrently. None of them is a caller/callee of another (a
    # function with a pending caller is held back), so their spec decisions don't influence each
    # other and can race safely; callees they queue are picked up in a later round, after their
    # caller, preserving the original caller-before-callee ordering.
    while True:
        pending = sorted(to_check - checked, key=_order_key)
        if not pending:
            break
        pending_set = set(pending)
        batch = [fqn for fqn in pending if not (callers_map.get(fqn, set()) & pending_set)]
        if not batch:
            # A pure cycle (every pending function has a pending caller): break it by taking
            # the single top-ordered function so the loop still makes progress.
            batch = [pending[0]]
        checked.update(batch)
        round_num += 1
        logging.info(
            "    [specs] round %d: checking %d function(s) (%d pending, %d checked so far)...",
            round_num, len(batch), len(pending), len(checked),
        )

        # Stage 1 (concurrent): decide each function's new spec — LLM-bound, no file writes.
        base = counter
        counter += len(batch)
        plans = [None] * len(batch)
        with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = {
                executor.submit(_plan_spec_update, fqn, base + i): i
                for i, fqn in enumerate(batch)
            }
            for future in concurrent.futures.as_completed(futures):
                i = futures[future]
                try:
                    plans[i] = future.result()
                except Exception:
                    logging.exception("Spec planning failed for %s", batch[i])
        applied = [p for p in plans if p]

        # Stage 2 (serial): write the new spec files and queue downward callees — no LLM, fast.
        # Kept serial so the shared to_check / changed_spec_files sets need no locking.
        queued_callees = 0
        for plan in applied:
            with open(plan["fpath"], "w") as f:
                f.write(plan["write_content"])
            changed_spec_files.add(os.path.relpath(plan["fpath"], extracted_dir))
            if plan["info_updated"]:
                for callee_fqn in _resolve_callee_fqns(
                    plan["fqn"], plan["updated_callees"], callees_map, edge_aliases_map
                ):
                    if callee_fqn not in checked:
                        to_check.add(callee_fqn)
                        queued_callees += 1
        logging.info(
            "    [specs] round %d: %d spec(s) rewritten, %d callee(s) queued for propagation.",
            round_num, len(applied), queued_callees,
        )

        # Stage 3 (concurrent): upward reconciliation. Each function whose [SPEC] changed needs
        # every caller's [INFO] entry for it reconciled. Group the work by caller file so edits
        # to one file are serialized while different caller files reconcile in parallel. Callers
        # sit above the batch in top-down order and are never themselves in the batch, so their
        # files don't collide with the Stage 2 writes.
        caller_updates = {}  # caller_fqn -> list of (callee_name, callee_new_spec)
        for plan in applied:
            callee_name = plan["fqn"].split("::")[-1]
            for caller_fqn in sorted(callers_map.get(plan["fqn"], ())):
                caller_updates.setdefault(caller_fqn, []).append((callee_name, plan["new_spec"]))

        if caller_updates:
            group_base = {}  # pre-assign a contiguous idx block per caller for unique artifacts
            for caller_fqn, updates in caller_updates.items():
                group_base[caller_fqn] = counter
                counter += len(updates)
            with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
                futures = {
                    executor.submit(
                        _reconcile_caller, caller_fqn, updates, group_base[caller_fqn]
                    ): caller_fqn
                    for caller_fqn, updates in caller_updates.items()
                }
                for future in concurrent.futures.as_completed(futures):
                    caller_fqn = futures[future]
                    try:
                        cpath = future.result()
                    except Exception:
                        logging.exception("Caller [INFO] reconciliation failed for %s", caller_fqn)
                        continue
                    if cpath:
                        changed_spec_files.add(os.path.relpath(cpath, extracted_dir))

    return sorted(changed_spec_files)

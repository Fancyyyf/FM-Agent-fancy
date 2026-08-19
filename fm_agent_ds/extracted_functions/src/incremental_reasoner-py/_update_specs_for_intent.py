def _update_specs_for_intent(
    proj_dir,
    work_dir,
    developer_intent,
    changed_functions,
    relevant_rel_files,
    extra_call_edges=None,
):
    """
    Re-generate the .spec.json (and dependent .info.json) sidecars of every function that is
    either changed or relevant to the developer intent, propagating to callees.

    Seeds from the changed functions (added/modified) and the relevant extracted-function
    files returned by collect_relevent_function_scope, then processes functions in top-down
    order (callers before callees). For each function, opencode reads its current .spec.json
    block and decides whether it must change to reflect developer_intent. A function with no
    existing .spec.json (e.g. one freshly added by the modification) instead has a spec
    generated from scratch the way the full run does. If a spec is written or generated, the
    new .spec.json is written back (source untouched), and then:

      - Downward: opencode decides whether the function's own .info.json (the expected
        specs of its callees) must change too, and any callee whose expected spec changed is
        queued to have its own spec file re-checked.
      - Upward: every caller's .info.json (which records this function as one of its
        callees) is reconciled with the function's new .spec.json so the two do not conflict
        (they need not be identical).

    Returns the sorted list of extracted-function files (paths relative to the
    extracted_functions dir) whose metadata sidecar was changed.
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
        Decide fqn's new metadata sidecars and return an apply-plan, or None to skip.

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
        with open(fpath, "r", errors="replace") as f:
            source = f.read()
        callee_names = sorted({c.split("::")[-1] for c in callees_map.get(fqn, ())})

        try:
            with open(f"{fpath}.spec.json", "r", encoding="utf-8") as f:
                old_spec = json.load(f)
            with open(f"{fpath}.info.json", "r", encoding="utf-8") as f:
                old_info = json.load(f)
        except (OSError, json.JSONDecodeError):
            old_spec, old_info = None, None

        if old_spec is None or old_info is None:
            # No existing specification (e.g. a freshly added, unspecced function) — generate
            # one from scratch the way the full run does, rather than skipping the function.
            caller_context = _collect_caller_context(
                fqn, callers_map, file_map, edge_aliases_map
            )
            result = _opencode_generate_spec(
                proj_dir, work_dir, idx, fqn, lang_key, "",
                developer_intent, callee_names, source, caller_context,
            )
        else:
            result = _llm_check_spec_update(
                proj_dir, work_dir, idx, fqn, lang_key, "",
                developer_intent, old_spec, old_info, callee_names, source,
            )

        if not result or not result.get("spec_updated"):
            return None
        new_spec = result.get("new_spec")
        if not isinstance(new_spec, dict):
            return None

        if old_info is None:
            # Freshly generated: take the .info.json object opencode produced. Treat it as
            # "updated" so its recorded callee expectations propagate downward below.
            new_info = result.get("new_info")
            if not isinstance(new_info, dict):
                new_info = {"callees": []}
            info_updated = True
        else:
            # Keep the existing .info.json unless opencode rewrote it. A modified function may
            # now call a different set of callees, so a fresh .info.json can legitimately be
            # created even when the function previously had none (old_info is None) — gate on
            # whether opencode produced a block, not on a prior block existing.
            info_updated = bool(result.get("info_updated"))
            new_info = result.get("new_info") if info_updated else old_info
            if not isinstance(new_info, dict):
                new_info = old_info

        return {
            "fqn": fqn,
            "fpath": fpath,
            "spec_dict": _normalize_spec_dict(new_spec),
            "info_dict": _normalize_info_dict(new_info),
            "info_updated": info_updated,
            "updated_callees": result.get("updated_callees") or [],
        }

    def _reconcile_caller(caller_fqn, updates, base_idx):
        """
        Reconcile caller_fqn's .info.json against a sequence of changed callees.

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
        changed = False
        for offset, (callee_name, callee_new_spec) in enumerate(updates):
            with open(cpath, "r", errors="replace") as f:
                csource = f.read()
            try:
                with open(f"{cpath}.info.json", "r", encoding="utf-8") as f:
                    c_info = json.load(f)
            except (OSError, json.JSONDecodeError):
                continue

            cresult = _llm_check_caller_info_update(
                proj_dir, work_dir, base_idx + offset, caller_fqn, callee_name, clang, "",
                callee_new_spec, c_info, csource,
            )
            if not cresult or not cresult.get("info_updated"):
                continue
            c_new_info = cresult.get("new_info")
            if not isinstance(c_new_info, dict):
                continue

            with open(f"{cpath}.info.json", "w", encoding="utf-8") as f:
                json.dump(_normalize_info_dict(c_new_info), f, indent=2, ensure_ascii=False)
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
        written = []
        for plan in applied:
            spec_path = f"{plan['fpath']}.spec.json"
            info_path = f"{plan['fpath']}.info.json"
            previous_sidecars = {}
            for sidecar_path in (spec_path, info_path):
                try:
                    with open(sidecar_path, "rb") as f:
                        previous_sidecars[sidecar_path] = f.read()
                except FileNotFoundError:
                    previous_sidecars[sidecar_path] = None

            with open(spec_path, "w", encoding="utf-8") as f:
                json.dump(plan["spec_dict"], f, indent=2, ensure_ascii=False)
            with open(info_path, "w", encoding="utf-8") as f:
                json.dump(plan["info_dict"], f, indent=2, ensure_ascii=False)

            if not is_file_ready(plan["fpath"]):
                for sidecar_path, previous_content in previous_sidecars.items():
                    if previous_content is None:
                        os.remove(sidecar_path)
                    else:
                        with open(sidecar_path, "wb") as f:
                            f.write(previous_content)
                logging.error(
                    "Incremental metadata write failed the final readiness check; restored %s",
                    plan["fpath"],
                )
                continue

            written.append(plan)
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
            round_num, len(written), queued_callees,
        )

        # Stage 3 (concurrent): upward reconciliation. Each function whose .spec.json changed
        # needs every caller's .info.json entry reconciled. Group by caller file so edits
        # to one file are serialized while different caller files reconcile in parallel. Callers
        # sit above the batch in top-down order and are never themselves in the batch, so their
        # files don't collide with the Stage 2 writes.
        caller_updates = {}  # caller_fqn -> list of (callee_name, callee_new_spec)
        for plan in written:
            callee_name = plan["fqn"].split("::")[-1]
            for caller_fqn in sorted(callers_map.get(plan["fqn"], ())):
                caller_updates.setdefault(caller_fqn, []).append((callee_name, plan["spec_dict"]))

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
                        logging.exception("Caller .info.json reconciliation failed for %s", caller_fqn)
                        continue
                    if cpath:
                        changed_spec_files.add(os.path.relpath(cpath, extracted_dir))

    return sorted(changed_spec_files)

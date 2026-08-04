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

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

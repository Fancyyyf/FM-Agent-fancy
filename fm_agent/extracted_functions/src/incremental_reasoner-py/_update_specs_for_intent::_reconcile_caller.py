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

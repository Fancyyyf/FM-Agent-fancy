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

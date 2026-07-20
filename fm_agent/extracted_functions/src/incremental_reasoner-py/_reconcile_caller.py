# [SPEC]
# Unit: src/incremental_reasoner-py/_reconcile_caller.py
#
# _reconcile_caller(caller_fqn, updates, base_idx) -> str | None
#
# Pre-condition:
#   - caller_fqn is a non-empty FQN of a caller function whose extracted file has valid [SPEC] and [INFO] blocks.
#   - updates is a list of (callee_fqn: str, callee_new_spec: str) tuples, each representing a callee whose [SPEC] changed.
#   - base_idx is a non-negative integer used to construct a unique artifact identifier.
#
# Post-condition:
#   - For each callee in updates, if the LLM determines that the callee's updated [SPEC] requires a change to the
#     caller's existing [INFO] entry for that callee, the caller's [INFO] block is replaced with a corrected
#     callee-expectation contract as determined by the LLM.
#   - The original source code (everything after the [SPEC] and [INFO] leading comment blocks) is preserved identically.
#   - If no update across all callees in updates results in a changed [INFO] block, or if the caller file cannot be
#     read, lacks a valid leading-spec block, or has no [INFO] block, the file is not modified.
#   - Returns the absolute path to the caller file if any [INFO] block was modified by this call; returns None otherwise.
# [SPEC]

# [INFO]
# _extract_leading_spec_comments(content, comment_prefix, spec_marker) -> str | None
#   Pre-condition: content is a non-empty string; comment_prefix and spec_marker are non-empty strings.
#   Post-condition: Returns the leading comment block containing [SPEC]/[INFO] markers as a contiguous string;
#     returns None if no valid leading-spec comment block exists.
# [SPLIT]
# _split_spec_and_info(leading, comment_prefix, spec_marker) -> (spec: str | None, info: str | None)
#   Pre-condition: leading is the string returned by _extract_leading_spec_comments; comment_prefix and spec_marker
#     are non-empty strings.
#   Post-condition: Returns a (spec, info) pair where spec is the [SPEC] block text and info is the [INFO] block text,
#     each extracted from leading. Either may be None if the corresponding block is absent or unparseable.
# [SPLIT]
# _llm_check_caller_info_update(proj_dir, work_dir, artifact_id, caller_fqn, callee_name, lang, comment_prefix,
#                                callee_new_spec, existing_info, source) -> dict | None
#   Pre-condition: caller_fqn, callee_name, lang, comment_prefix, callee_new_spec, existing_info, and source are
#     non-empty strings; proj_dir and work_dir are valid directory paths; artifact_id is a non-negative integer.
#   Post-condition: Returns a dict with keys "info_updated" (bool) and, when true, "new_info" (str) containing
#     the corrected [INFO] entry for the callee that is consistent with the callee's new [SPEC].
#     Returns None if the LLM call fails or produces unparseable output.
# [INFO]

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
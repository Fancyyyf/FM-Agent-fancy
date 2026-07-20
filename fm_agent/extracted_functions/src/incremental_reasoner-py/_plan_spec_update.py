# [SPEC]
# Unit: src/incremental_reasoner.py
#
# _plan_spec_update(fqn, idx)
#
# Pre-condition:
#   - fqn is a non-empty fully-qualified function name string (e.g., "src::module::func")
#   - idx is a non-negative integer used only for correlation with output trace entries
#   - The following module-level state must be initialized before any call:
#     file_map: maps each known FQN to its extracted-function file path on disk
#     EXT_TO_LANG: maps file extensions (without leading dot) to language keys
#     LANG_CONFIG: maps each language key to a dict containing at least the keys
#       "comment_prefix" (the single-line comment marker for that language) and
#       "spec_marker" (the delimiter string that marks spec blocks, e.g., "[SPEC]")
#     callees_map: maps each FQN to a set of callee FQNs (may be empty)
#     callers_map: maps each FQN to a set of caller FQNs (may be empty)
#     edge_aliases_map: maps callee FQNs to alias name strings used for caller-context
#       matching across differently-named call sites
#     proj_dir: absolute path to the project root directory
#     work_dir: absolute path to the fm_agent workspace directory
#     developer_intent: a non-empty string describing the developer's intent for
#       the incremental change
#
# Post-condition:
#   - Returns None when any of the following holds:
#       • fqn is absent from file_map, or the resolved file path does not exist on disk
#       • the file's extension maps to no language key in EXT_TO_LANG
#       • after consulting the LLM, no spec change is indicated
#         (result["spec_updated"] is absent or falsy)
#       • the new spec string produced by the LLM is empty after stripping whitespace
#   - When a pre-existing spec comment block is absent, a fresh spec is generated
#     by sending the full source and caller context to an LLM that writes a
#     behavioral [SPEC]/[INFO] block from scratch; when a pre-existing block exists,
#     a lighter LLM call determines whether the block needs rewriting
#   - Otherwise returns a dict (the "apply plan") with exactly these keys:
#       fqn: the input FQN (string)
#       fpath: the absolute path to the extracted-function file (string)
#       write_content: a string whose first byte is the new [SPEC] block, followed
#         by a blank line, optionally followed by the [INFO] block and a blank line,
#         and ending with the original function source code; the source portion is
#         byte-for-byte identical to the input source (only leading spec comments
#         are replaced)
#       new_spec: the raw [SPEC] block text including its delimiters (string)
#       info_updated: True if and only if an [INFO] block was either created for
#         the first time or replaced with different content (bool)
#       updated_callees: a list of short callee names (the last component of each
#         callee FQN) whose own specs were reported as updated by the LLM that
#         produced this plan (list of strings, may be empty)
#   - This function performs LLM calls and disk reads but performs no file writes;
#     the caller is responsible for applying write_content to the file at fpath
#   - When the function returns a plan, write_content begins with a comment-prefixed
#     [SPEC] marker line and ends with the line-comment-prefixed [SPEC] closing
#     marker line, followed by at most one blank line before the [INFO] block
#     (if present) and at most one blank line before the source code
# [SPEC]

# [INFO]
# _extract_leading_spec_comments(content, comment_prefix, spec_marker)
#   Pre-condition: content is a non-empty string (the complete file contents);
#     comment_prefix is the language's single-line comment marker;
#     spec_marker is the delimiter (e.g., "[SPEC]") that identifies spec blocks
#   Post-condition: Returns the prefix of content that begins at byte 0 and ends
#     at the last line containing a spec comment (delimited by spec_marker), or
#     None when no spec comment lines are present; the returned string preserves
#     all line terminators of the original
# [SPLIT]
# _split_spec_and_info(leading, comment_prefix, spec_marker)
#   Pre-condition: leading is the non-None string returned by _extract_leading_spec_comments
#   Post-condition: Returns a 2-tuple (spec_block, info_block); spec_block is the
#     [SPEC]-delimited portion of leading; info_block is the [INFO]-delimited
#     portion of leading, or None when no [INFO] section exists; both strings
#     include their delimiter lines
# [SPLIT]
# _collect_caller_context(fqn, callers_map, file_map, edge_aliases_map)
#   Pre-condition: fqn is a non-empty FQN; callers_map maps FQNs to sets of caller
#     FQNs; file_map maps FQNs to file paths; edge_aliases_map maps callee FQNs to
#     alias name strings
#   Post-condition: Returns a formatted string containing the [SPEC]-delimited
#     pre- and post-conditions of every direct caller of fqn whose spec has been
#     written to disk; returns an empty string when fqn has no callers or no
#     caller has an available spec; the returned string includes the FQN of each
#     contributing caller for traceability
# [SPLIT]
# _opencode_generate_spec(proj_dir, work_dir, idx, fqn, lang_key, comment_prefix,
#     developer_intent, callee_names, source, caller_context)
#   Pre-condition: All arguments are non-None; source is the complete source code
#     of the function; callee_names is a sorted list of short callee names (may be
#     empty); caller_context is the formatted caller-expectation string produced by
#     _collect_caller_context (may be empty)
#   Post-condition: Blocks until the OpenCode subprocess terminates, then returns
#     a JSON dict with at least the keys "spec_updated" (bool, True when a new
#     spec was written) and "new_spec" (string, the generated [SPEC] block);
#     optionally includes "new_info" (string), "info_updated" (bool), and
#     "updated_callees" (list of strings); returns None when the subprocess exits
#     non-zero or produces output that cannot be parsed as valid JSON
# [SPLIT]
# _llm_check_spec_update(proj_dir, work_dir, idx, fqn, lang_key, comment_prefix,
#     developer_intent, old_spec, old_info, callee_names, source)
#   Pre-condition: old_spec is the existing [SPEC] block text or None; old_info is
#     the existing [INFO] block text or None; all other arguments follow the same
#     contract as _opencode_generate_spec
#   Post-condition: Blocks until the LLM call completes, then returns a JSON dict
#     with the same key contract as _opencode_generate_spec, but evaluating whether
#     an existing spec must be rewritten rather than generating from scratch;
#     returns None on LLM failure or unparseable output
# [INFO]

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

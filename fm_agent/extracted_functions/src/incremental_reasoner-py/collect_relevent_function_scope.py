# [SPEC]
# Unit: fm_agent/extracted_functions/src/incremental_reasoner-py/collect_relevent_function_scope.py
#
# collect_relevent_function_scope(proj_dir, developer_intent, changed_functions, range=None) -> list[str]
#
# Pre-condition:
#   - proj_dir is a path to a project directory whose fm_agent/ subdirectory contains phases.json
#     (with a "phases" list of phase objects, each containing a "modules" list) and extracted_functions/
#   - developer_intent is a non-empty string describing the modification goal
#   - changed_functions is a dict mapping absolute source file paths to dicts with string-list values
#     under at least the keys "added", "modified", and "removed"
#   - range is None or a non-negative integer
#
# Post-condition:
#   - Returns a list of paths, each relative to the extracted_functions/ directory, ordered by
#     descending relevance to developer_intent; paths with equal relevance are ordered lexicographically
#   - Every returned path refers to an existing regular file under extracted_functions/
#   - When range is not None, the returned list has length ≤ range
#   - Returns an empty list when phases.json defines no modules, or when no module is selected
#     by the relevance assessment
#   - A module is selected when EITHER its natural-language description (as recorded in phases.json)
#     is assessed as relevant to the developer intent, OR the module contains at least one source file
#     whose path, relativized against proj_dir, matches a key in changed_functions
#   - Within each selected module, a source file is included only when its content is assessed as
#     relevant to the developer intent, EXCEPT that every source file present in changed_functions
#     is included unconditionally
#   - When the per-module file-relevance assessment cannot be obtained, every source file in that
#     module is included
#   - Within each included source file, the set of extracted functions whose relevance scores
#     (computed from heuristic signals derived from developer_intent) rank within the top of that file
#     are included
#   - When per-file function ranking is unavailable for an included source file, every extracted
#     function from that file is included
#   - Multiple extracted-function files mapping to the same source-level function are deduplicated,
#     keeping only the occurrence with the highest relevance score
# [SPEC]

# [INFO]
# rank_functions_in_file(filepath, src_path, issue, signals, top_k, llm_client=None,
#                        llm_model='', llm_trigger=LLM_TRIGGER_FUNCS, llm_top_k=LLM_TOP_K,
#                        llm_confidence_threshold=LLM_CONFIDENCE_THRESHOLD, proj_dir=None)
#                        -> list[dict]
#   Pre-condition: src_path is a Path to an existing source file; filepath is a relative-path
#     label; issue is a non-empty string; signals is a dict structured as the output of
#     _parse_issue_signals with keys 'traceback_funcs', 'backtick_idents', 'dotted_refs',
#     'dotted_classes', 'plain_idents', 'exception_types', 'all_words'; top_k, llm_trigger,
#     and llm_top_k are positive integers; llm_confidence_threshold is a positive float
#   Post-condition: Returns a list of dicts sorted in descending order by 'score' (float, rounded
#     to 3 decimal places), each containing keys 'file', 'name', 'lineno', 'end_lineno', 'score',
#     and 'reason'. Length ≤ top_k. Returns an empty list when the source file has no parseable
#     functions. Every 'name' is unique within the result and names a function defined in src_path.
# _extracted_files_by_method(func_dir) -> dict-like
#   Pre-condition: func_dir is a filesystem path (may or may not be an existing directory)
#   Post-condition: Returns a mutable dict-like mapping from string keys (function names) to
#     lists of absolute filesystem paths, each list containing one or more entries. When
#     func_dir is not an existing directory, returns an empty mapping. When func_dir is an
#     existing directory, every regular file reachable by recursive descent is indexed under
#     one or two keys using the file's basename stem (name without final extension): always
#     the full stem, and if the stem contains "::", also the substring after the last "::"
#     (the bare method name). The order of paths within each list reflects the order they
#     were encountered during traversal. Accessing a missing key returns an empty list
#     without modifying the mapping.
# [INFO]

def collect_relevent_function_scope(proj_dir, developer_intent, changed_functions, range=None):
    """
    Select the functions relevant to developer_intent and return the most relevant ones.

    The module/phase plan in proj_dir/fm_agent/phases.json describes the project as a set
    of modules, each with a natural-language description and a list of source_files. This
    narrows the scope to the developer's intent in three passes:

      1. Module selection — a direct LLM call is given the module descriptions (already
         parsed from phases.json) and picks the modules relevant to the intent.
      2. File selection — for each relevant module, opencode reads that module's source
         files and picks the files relevant to the intent.
      3. Function selection — the function-localization algorithm from scope.py ranks the
         functions in each chosen file by relevance to the intent (heuristic signal scoring
         with call-graph and class-scope enrichments) and keeps the top-ranked functions
         per file.

    range, when given, caps the result to the first (most relevant) `range` functions; pass
    None to return all of them.

    Returns the selected extracted-function file paths (relative to the extracted_functions
    dir, matching the convention used elsewhere in this module), ordered by descending
    relevance score and truncated to the first `range` entries. Returns an empty list when
    phases.json has no modules or opencode selects none / fails to produce a result.
    """
    work_dir = os.path.join(proj_dir, "fm_agent")
    extracted_dir = os.path.join(work_dir, "extracted_functions")

    phases_data = _load_phases(work_dir)

    # Flatten every module across all phases so we can match opencode's selection back to
    # concrete modules (module names can repeat across phases, so keep the phase number too).
    modules = []  # list of (phase_num, module_dict)
    for phase_info in phases_data.get("phases", []):
        phase_num = phase_info.get("phase")
        for module in phase_info.get("modules", []):
            modules.append((phase_num, module))

    if not modules:
        logging.info("    [scope] no modules in phases.json; nothing to select.")
        return []

    changed_source_rels = {
        os.path.relpath(abs_src, proj_dir).replace(os.sep, "/")
        for abs_src in changed_functions
    }
    logging.info("    [scope] pass 1/3: selecting relevant modules from %d module(s)...", len(modules))

    # Pass 1: module selection. The module descriptions are already parsed from phases.json
    # above, so rather than have opencode read the file, inline the catalog and make a direct
    # LLM call that returns the selection as JSON.
    module_catalog = "\n".join(
        f"- phase {phase_num}, name `{module.get('name', '(unnamed)')}`: "
        f"{(module.get('description') or '').strip() or '(no description)'}"
        for phase_num, module in modules
    )
    module_prompt = (
        "# Select Relevant Modules\n\n"
        "You are triaging which parts of a codebase are relevant to a developer's intent.\n\n"
        "Each module below has a `phase` number, a `name`, and a `description`. Using each "
        "module's description, decide which modules are relevant to the developer intent — a "
        "module is relevant if the developer intent is likely to affect it or depend on it.\n\n"
        "## Modules\n\n"
        f"{module_catalog}\n\n"
        "## Developer intent\n\n"
        f"{developer_intent}\n\n"
        "## Output\n\n"
        "Return ONLY a JSON array of objects, each "
        '`{"phase": <phase number>, "name": "<module name>"}`, naming exactly the modules you '
        "judged relevant (reuse the same `phase` and `name` values from the list above). Use "
        "`[]` if no module is relevant. Do not include Markdown, tags, or prose outside the JSON array.\n"
    )
    selection = _llm_select_json(
        work_dir,
        module_prompt,
        stage="select_relevant_modules",
        validator=_validate_module_selection,
        schema_description='[{"phase": integer, "name": "non-empty string"}]',
    )
    if selection is None:
        selection = []

    selected_keys = set()
    if isinstance(selection, list):
        for item in selection:
            if isinstance(item, dict) and "name" in item:
                selected_keys.add((item.get("phase"), item["name"]))

    relevant_modules = [
        (phase_num, module) for phase_num, module in modules
        if (phase_num, module.get("name")) in selected_keys
        or any(sf.replace("\\", "/") in changed_source_rels for sf in module.get("source_files", []))
    ]
    if not relevant_modules:
        logging.info("    [scope] pass 1/3: no relevant modules selected.")
        return []
    for phase_num, module in relevant_modules:
        logging.info(
            "    [scope] pass 1/3: relevant module: phase %s / %s",
            phase_num, module.get("name", "(unnamed)"),
        )
    logging.info(
        "    [scope] pass 2/3: %d relevant module(s); selecting relevant files per module...",
        len(relevant_modules),
    )

    # Pass 2: file selection. For each relevant module, opencode reads that module's source
    # files and narrows them to the files relevant to the intent. The result is a synthetic
    # module dict carrying only the chosen source_files; on opencode failure we fall back to
    # the module's full file list so the scope is never silently dropped.
    filtered_modules = []
    for idx, (phase_num, module) in enumerate(relevant_modules):
        module_name = module.get("name", f"module_{idx}")
        source_files = module.get("source_files", [])
        if not source_files:
            continue

        source_set = set(source_files)
        changed_in_module = [
            sf for sf in source_files
            if sf.replace("\\", "/") in changed_source_rels
        ]
        file_list_md = "\n".join(f"- `{sf}`" for sf in source_files)
        file_prompt = (
            "# Select Relevant Files\n\n"
            f"You are triaging which files of the module `{module_name}` are relevant to a "
            "developer intent.\n\n"
            "## Steps\n\n"
            "1. Read each of the module source files listed below.\n"
            "2. Decide which files are relevant to the developer intent -- a file is relevant "
            "if the developer intent is likely to affect it or depend on its behavior.\n"
            f"3. Write your answer to `fm_agent/relevant_files_{idx}.json` as a JSON array of "
            "the relevant file paths, each copied verbatim from the list below. Write `[]` if "
            "no file is relevant. Write ONLY that file; do not modify any other project "
            "files.\n\n"
            "## Module source files\n\n"
            f"{file_list_md}\n\n"
            "## Developer intent\n\n"
            f"{developer_intent}\n"
        )
        file_selection = _opencode_select_json(
            proj_dir,
            work_dir,
            os.path.join("fm_agent", f"select_relevant_files_{idx}.md"),
            file_prompt,
            os.path.join("fm_agent", f"relevant_files_{idx}.json"),
            stage="select_relevant_files",
            input_files=[f"fm_agent/select_relevant_files_{idx}.md", *source_files],
        )

        if isinstance(file_selection, list):
            chosen = [sf for sf in file_selection if sf in source_set]
            for sf in changed_in_module:
                if sf not in chosen:
                    chosen.append(sf)
        else:
            # opencode failed for this module; keep all files rather than drop scope.
            chosen = list(source_files)

        if chosen:
            filtered_modules.append({**module, "source_files": chosen})
            logging.info(
                "    [scope] pass 2/3: module %s -> %d relevant file(s): %s",
                module_name, len(chosen), ", ".join(chosen),
            )

    if not filtered_modules:
        logging.info("    [scope] pass 2/3: no relevant files selected.")
        return []
    logging.info(
        "    [scope] pass 3/3: ranking functions in %d module(s) by relevance...",
        len(filtered_modules),
    )

    # Pass 3: function selection via the scope.py localization algorithm. For each chosen
    # file, rank its functions by relevance to the developer intent and keep the top-ranked
    # ones, then map each selected function back to its extracted-function file
    # (run_extraction writes one file per function at <func dir>/<func_name>.<ext>). A file
    # scope.py cannot analyze yields no ranking, so we fall back to all of its extracted
    # functions rather than drop it from scope.
    signals = _parse_issue_signals(developer_intent)
    repo_dir = Path(proj_dir)

    # Collect each selected extracted-function file with its relevance score, keeping the
    # highest score seen for a given file. Files scope.py cannot localize within contribute
    # all of their functions at a neutral 0.0 score (so a genuinely high-scoring function
    # always outranks them).
    scored = {}  # rel_path -> best score

    def _record(rel_path, score):
        if rel_path not in scored or score > scored[rel_path]:
            scored[rel_path] = score

    for module in filtered_modules:
        for src_rel in module.get("source_files", []):
            func_dir = _extracted_func_dir(extracted_dir, src_rel)
            if not os.path.isdir(func_dir):
                continue
            ext = src_rel.rsplit(".", 1)[-1] if "." in src_rel else ""

            ranked = []
            src_path = repo_dir / src_rel
            if src_path.exists():
                ranked = rank_functions_in_file(
                    filepath=src_rel,
                    src_path=src_path,
                    issue=developer_intent,
                    signals=signals,
                    proj_dir=proj_dir,
                )

            if ranked:
                # Keep the extracted-function file for each selected function name.
                # The dual-key index resolves the name whether scope reports it bare
                # ("Flush") or class-qualified ("LocalStorage::Flush"); a bare name
                # matching two classes keeps both members — safe for scope.
                by_method = _extracted_files_by_method(func_dir)
                for f in ranked:
                    cands = by_method.get(f["name"]) or by_method.get(
                        re.sub(r"_\d+$", "", f["name"]), []
                    )
                    for cand in cands:
                        _record(os.path.relpath(cand, extracted_dir), f.get("score", 0.0))
                logging.info(
                    "    [scope] pass 3/3: %s -> %s",
                    src_rel,
                    ", ".join(f"{f['name']}={f.get('score', 0.0):.2f}" for f in ranked),
                )
            else:
                # scope.py could not localize within this file — keep all of its
                # extracted-function files (walked; the layout is flat but os.walk
                # stays robust to any legacy nested file).
                for root, _dirs, fnames in os.walk(func_dir):
                    for fname in fnames:
                        cand = os.path.join(root, fname)
                        if os.path.isfile(cand):
                            _record(os.path.relpath(cand, extracted_dir), 0.0)

    # Order by descending relevance score (path as a deterministic tie-breaker), then keep
    # only the first `range` functions when a limit is given.
    ordered = sorted(scored, key=lambda p: (-scored[p], p))
    if range is not None:
        ordered = ordered[:range]
    for rel_path in ordered:
        logging.info("    [scope] selected function: %s (score %.2f)", rel_path, scored[rel_path])
    return ordered

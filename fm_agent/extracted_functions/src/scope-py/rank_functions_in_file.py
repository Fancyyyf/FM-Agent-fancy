# [SPEC]
# Unit: fm_agent/extracted_functions/src/scope-py/rank_functions_in_file.py
#
# rank_functions_in_file(filepath, src_path, issue, signals, top_k=TOP_K,
#                        llm_client=None, llm_model='',
#                        llm_trigger=LLM_TRIGGER_FUNCS, llm_top_k=LLM_TOP_K,
#                        llm_confidence_threshold=LLM_CONFIDENCE_THRESHOLD,
#                        proj_dir=None) -> list[dict]
#
# Pre-condition:
#   - src_path is a Path to an existing source file.
#   - filepath is a human-readable label identifying the file.
#   - issue is a string describing developer intent.
#   - signals is a dict[str, set[str]] with the same keys produced by
#     _parse_issue_signals: 'traceback_funcs', 'backtick_idents', 'dotted_refs',
#     'dotted_classes', 'plain_idents', 'exception_types', 'all_words'.
#   - top_k is a positive integer.
#   - llm_trigger, llm_top_k are positive integers.
#   - llm_confidence_threshold is a positive float.
#
# Post-condition:
#   - If the file contains zero parseable functions, returns an empty list.
#   - Otherwise, returns a list of dicts sorted in descending order by 'score'.
#   - Each returned dict contains the keys: 'file' (str, equal to filepath),
#     'name' (str), 'lineno' (int, 1‑based start line), 'end_lineno' (int,
#     1‑based end line), 'score' (float, rounded to 3 decimal places), and
#     'reason' (str, one of "heuristic", "llm", "heuristic_pad").
#   - The returned list length is at most top_k.
#   - Every 'name' in the result is unique; if a name appeared in multiple
#     positions within the file, only the occurrence with the highest score is kept.
#   - Every 'name' in the result corresponds to a function actually defined
#     in the source file.
#   - Scores reflect relevance to the issue as judged against the signals.
#   - When an LLM client is provided AND EITHER the highest heuristic score among
#     all unique functions is below llm_confidence_threshold OR the count of
#     unique functions in the file is at least llm_trigger, LLM‑based re‑ranking
#     is attempted. On success, entries chosen by the LLM carry reason="llm"
#     and remaining heuristic fillers up to top_k carry reason="heuristic_pad".
#   - When LLM re‑ranking is not attempted or fails, all returned entries carry
#     reason="heuristic".
# [SPEC]

# [INFO]
# _parse_file(src_path: Path, proj_dir: str | None) -> (list[dict] | None, list[str], list[dict] | None)
#   Pre-condition: src_path is the path to a source file that exists.
#   Post-condition: Returns a tuple of (funcs_info, source_lines, classes).
#     funcs_info is None or a list of dicts, each describing a function in the
#     file with at minimum 'name', 'start', and 'end' keys. source_lines is the
#     list of source text lines. classes is None or a list of dicts describing
#     each class.
# [SPLIT]
# _rank_functions(funcs_info: list[dict], classes: list[dict], signals: dict[str, set[str]]) -> list[dict]
#   Pre-condition: funcs_info is a non-empty list of function descriptor dicts,
#     each containing at minimum 'name', 'start', 'end' keys. classes is a list
#     of class descriptor dicts. signals has the structure returned by
#     _parse_issue_signals.
#   Post-condition: Returns a list of dicts, each containing at minimum 'name',
#     'start', 'end', and 'score' (float), sorted in descending order by 'score'.
#     Scores are heuristic relevance values derived from the signals.
# [SPLIT]
# _llm_rerank(deduped_ranked: list[dict], source_lines: list[str], filepath: str,
#             issue: str, llm_top_k: int, llm_client, llm_model: str) -> list[str] | None
#   Pre-condition: deduped_ranked is a non-empty list of ranked function dicts
#     with unique names; source_lines is the full source text as a list of lines;
#     llm_client is a live LLM client; llm_model is a non-empty model identifier.
#   Post-condition: On success, returns a list of function names re-ranked in
#     descending order of relevance by the LLM, of length at most llm_top_k.
#     On failure, returns None or empty/falsy.
# [INFO]

def rank_functions_in_file(
    filepath: str,
    src_path: Path,
    issue: str,
    signals: dict[str, set[str]],
    top_k: int = TOP_K,
    llm_client: Any = None,
    llm_model: str = '',
    llm_trigger: int = LLM_TRIGGER_FUNCS,
    llm_top_k: int = LLM_TOP_K,
    llm_confidence_threshold: float = LLM_CONFIDENCE_THRESHOLD,
    proj_dir: str | None = None,
) -> list[dict]:
    """
    Rank functions in a single file by relevance to the issue.

    proj_dir, when given, lets the non-Python parse path resolve function boundaries from
    codegraph (via extract._function_spans) instead of the regex fallback.

    Returns a list of dicts (file, name, lineno, end_lineno, score, reason),
    sorted descending by score, length ≤ top_k.
    """
    funcs_info, source_lines, classes = _parse_file(src_path, proj_dir=proj_dir)
    if funcs_info is None or not funcs_info:
        print(f"  [scope] {filepath}: no functions found, skipping")
        return []

    # Stage 1: heuristic scoring with all enrichments
    ranked = _rank_functions(funcs_info, classes or [], signals)

    # Deduplicate by name (keep highest-scored occurrence per name)
    seen_names: dict[str, dict] = {}
    deduped_ranked: list[dict] = []
    for f in ranked:
        if f['name'] not in seen_names:
            seen_names[f['name']] = f
            deduped_ranked.append(f)

    # ── print per-file function scores ──────────────────────────────────────
    print(f"\n{'─' * 70}")
    print(f"FILE: {filepath}  ({len(deduped_ranked)} unique functions)")
    if classes:
        class_names = [c['name'] for c in classes]
        print(f"  classes found: {class_names}")
    print(f"  {'rank':>4}  {'score':>8}  {'name'}")
    print(f"  {'----':>4}  {'-------':>8}  {'----'}")
    for rank, f in enumerate(deduped_ranked, 1):
        marker = "  <<" if rank <= top_k else ""
        print(f"  {rank:>4}  {f['score']:>8.3f}  {f['name']}  (L{f['start']}-{f['end']}){marker}")

    candidates = deduped_ranked[:top_k]
    reason = 'heuristic'
    heuristic_top_score = deduped_ranked[0]['score'] if deduped_ranked else 0.0

    # Stage 2: LLM re-ranking (optional)
    use_llm = (
        llm_client is not None
        and (
            heuristic_top_score < llm_confidence_threshold
            or len(deduped_ranked) >= llm_trigger
        )
    )
    if use_llm:
        llm_names = _llm_rerank(
            deduped_ranked, source_lines, filepath, issue,
            llm_top_k, llm_client, llm_model,
        )
        if llm_names:
            func_map = {f['name']: f for f in deduped_ranked}
            seen: set[str] = set()
            merged: list[dict] = []
            for name in llm_names:
                if name in func_map and name not in seen:
                    f = dict(func_map[name])
                    f['reason'] = 'llm'
                    merged.append(f)
                    seen.add(name)
            for f in deduped_ranked:
                if f['name'] not in seen and len(merged) < top_k:
                    f = dict(f)
                    f['reason'] = 'heuristic_pad'
                    merged.append(f)
                    seen.add(f['name'])
            candidates = merged[:top_k]
            reason = 'llm'
        else:
            logger.warning("LLM rerank failed for %s, falling back to heuristic", filepath)

    result = []
    for f in candidates:
        result.append({
            'file':        filepath,
            'name':        f['name'],
            'lineno':      f['start'],
            'end_lineno':  f['end'],
            'score':       round(f.get('score', 0.0), 3),
            'reason':      f.get('reason', reason),
        })

    print(f"  → selected ({reason}): " +
          ", ".join(f"{r['name']} ({r['score']:.3f})" for r in result))
    return result

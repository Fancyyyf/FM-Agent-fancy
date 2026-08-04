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

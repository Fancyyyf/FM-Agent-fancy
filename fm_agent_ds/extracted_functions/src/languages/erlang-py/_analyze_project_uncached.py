def _analyze_project_uncached(proj_dir: str) -> ErlangAnalysis:
    proj_dir = os.path.abspath(proj_dir)
    files = _erlang_files(proj_dir)
    if not files:
        return ErlangAnalysis(functions={}, edges={})

    functions: dict[str, list[tuple[str, str]]] = {}
    edges: dict[tuple[str, str], set[str]] = {}
    spans: dict[str, list[tuple[str, int, int]]] = {}
    sources = {
        path: Path(path).read_text(encoding="utf-8", errors="replace")
        for path in files
    }

    with ElpClient(proj_dir) as client:
        server_info = client.initialize(files[0], sources[files[0]])
        for path in files[1:]:
            client.open_document(path, sources[path])
        for path in files:
            source = sources[path]
            source_index = _SourceIndex.build(source)
            caller_module = _caller_module(path)
            uri = Path(path).as_uri()
            symbols = client.request(
                "textDocument/documentSymbol", {"textDocument": {"uri": uri}}
            ) or []
            file_functions = []
            file_spans = []
            seen = set()
            for symbol in symbols:
                if symbol.get("kind") != _FUNCTION_KIND:
                    continue
                symbol_range = _symbol_range(symbol)
                if not symbol_range:
                    continue
                symbol_uri = _symbol_uri(symbol, uri)
                try:
                    function_id = _function_id(symbol_uri, symbol.get("name", ""))
                except ValueError:
                    logging.warning("Ignoring malformed ELP function symbol: %r", symbol)
                    continue
                if function_id in seen:
                    continue
                seen.add(function_id)
                file_functions.append((function_id, source_index.source_for_range(symbol_range)))
                start_line, end_line = _symbol_line_span(symbol_range)
                file_spans.append((function_id, start_line, end_line))

                caller_key = (function_id, caller_module)
                edges.setdefault(caller_key, set())
                selection = symbol.get("selectionRange") or symbol_range
                prepared = client.request(
                    "textDocument/prepareCallHierarchy",
                    {
                        "textDocument": {"uri": symbol_uri},
                        "position": selection["start"],
                    },
                ) or []
                if not prepared:
                    continue
                item = None
                for candidate in prepared:
                    if not isinstance(candidate, dict):
                        continue
                    try:
                        candidate_id = _function_id(
                            candidate.get("uri", symbol_uri),
                            candidate.get("name", ""),
                        )
                    except (TypeError, ValueError):
                        continue
                    if candidate_id == function_id:
                        item = candidate
                        break
                if item is None:
                    continue
                outgoing = client.request(
                    "callHierarchy/outgoingCalls", {"item": item}
                ) or []
                for call in outgoing:
                    target = call.get("to") or {}
                    try:
                        target_id = _function_id(
                            target.get("uri", symbol_uri), target.get("name", "")
                        )
                    except ValueError:
                        continue
                    edges[caller_key].add(target_id)

            if file_functions:
                functions[path] = file_functions
                spans[path] = file_spans

    return ErlangAnalysis(
        functions=functions,
        edges=edges,
        spans=spans,
        server_info=server_info,
    )

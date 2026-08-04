def _persist_analysis(proj_dir: str, fingerprint: tuple, analysis: ErlangAnalysis):
    """Persist successful ELP output for diagnostics and reproducible inspection."""
    root = os.path.abspath(proj_dir)
    output_dir = os.path.join(root, ".codegraph")
    output_path = os.path.join(output_dir, "erlang_callgraph.json")

    functions = []
    caller_files = {}
    for path, file_functions in sorted(analysis.functions.items()):
        rel_path = os.path.relpath(path, root).replace(os.sep, "/")
        caller_module = _caller_module(path)
        for function_id, _source in file_functions:
            functions.append({"id": function_id, "file": rel_path})
            caller_files[(function_id, caller_module)] = rel_path

    edges = [
        {
            "caller": caller,
            "caller_module": caller_module,
            "caller_file": caller_files.get((caller, caller_module)),
            "callee": callee,
        }
        for (caller, caller_module), callees in sorted(analysis.edges.items())
        for callee in sorted(callees)
    ]
    document = {
        "schema_version": 1,
        "status": "success",
        "backend": "elp",
        "server_info": analysis.server_info,
        "elp_command": list(_elp_argv()),
        "project_fingerprint": _fingerprint_digest(fingerprint),
        "functions": functions,
        "edges": edges,
    }

    os.makedirs(output_dir, exist_ok=True)
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=output_dir,
            prefix=".erlang_callgraph.",
            suffix=".tmp",
            delete=False,
        ) as stream:
            temp_path = stream.name
            json.dump(document, stream, indent=2, ensure_ascii=False)
            stream.write("\n")
        os.replace(temp_path, output_path)
    finally:
        if temp_path and os.path.exists(temp_path):
            try:
                os.unlink(temp_path)
            except OSError:
                pass

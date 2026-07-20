# [SPEC]
# Unit: src/languages/erlang-py/_persist_analysis.py
#
# _persist_analysis(proj_dir: str, fingerprint: tuple, analysis: ErlangAnalysis)
#
# Pre-condition:
#   - proj_dir is a non-empty string that resolves to an absolute filesystem path
#   - fingerprint is a hashable tuple representing the project state fingerprint
#     that uniquely identifies the version of the project being analyzed
#   - analysis is a populated ErlangAnalysis object with non-None .functions,
#     .edges, .spans, and .server_info attributes
#
# Post-condition:
#   - Creates or overwrites the file .codegraph/erlang_callgraph.json under the
#     directory identified by the resolved absolute path of proj_dir
#   - The output file contains a single JSON object with the following guaranteed
#     keys: "schema_version" (integer, value 1), "status" (string, value
#     "success"), "backend" (string, value "elp"), "server_info" (the contents
#     of analysis.server_info), "elp_command" (a list of strings), and
#     "project_fingerprint" (a string digest)
#   - The JSON object contains a "functions" key whose value is a list of
#     {"id": function_id, "file": relative_path} objects, one per function in
#     analysis.functions, where relative_path is the file path relative to the
#     resolved proj_dir using "/" separators
#   - The JSON object contains an "edges" key whose value is a list of
#     {"caller", "caller_module", "caller_file", "callee"} objects, one per
#     callee in analysis.edges, where "caller_file" is the relative path of the
#     file containing the caller function
#   - The write to the output file is atomic: the file at the target path is
#     replaced only after the full JSON document has been written to a temporary
#     file; if the write is interrupted, the target file either retains its
#     previous contents (or does not exist) with no partial data
#   - Raises OSError when the output directory cannot be created or when the
#     output file cannot be written or replaced
# [SPEC]

# [INFO]
# _caller_module(path: str) -> str
#   Pre-condition: path is an absolute file path to a source file
#   Post-condition: Returns the Erlang module name derived from the file path
#     according to Erlang module naming conventions
# [SPLIT]
# _fingerprint_digest(fingerprint: tuple) -> str
#   Pre-condition: fingerprint is a hashable tuple
#   Post-condition: Returns a deterministic string digest that uniquely
#     represents the given fingerprint; identical fingerprints produce identical
#     digests
# [SPLIT]
# _elp_argv() -> list[str]
#   Pre-condition: None (the ELP command is configured in the environment)
#   Post-condition: Returns the ELP command-line argument list used to invoke
#     the Erlang Language Platform backend
# [INFO]

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

def parse_input_function(file_path):
    """
    Parse an extracted source file and its adjacent JSON metadata sidecars.

    1. func: complete source file, with comments removed
    2. nl_spec: reasoner-facing text rebuilt from .spec.json
    3. knowledge: a map from .info.json callee entries

    Returns:
        tuple: (func, nl_spec, knowledge)
    """
    with open(file_path, 'r') as file:
        func = file.read()

    spec = _load_sidecar_json(file_path, ".spec.json")
    info = _load_sidecar_json(file_path, ".info.json")
    nl_spec = format_spec_for_reasoner(spec) if spec else ""
    knowledge = format_info_for_reasoner(info) if info else FunctionSpecMap()

    func = _remove_func_comments(func)

    # Add line numbers to each line in func
    func_lines = func.split('\n')
    numbered_lines = [f"Line {i+1}: {line}" for i, line in enumerate(func_lines)]
    func = '\n'.join(numbered_lines)

    return func, nl_spec, knowledge

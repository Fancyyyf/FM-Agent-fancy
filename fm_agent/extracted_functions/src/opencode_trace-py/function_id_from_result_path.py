def function_id_from_result_path(path):
    rel = path.replace("\\", "/")
    prefix = "fm_agent/logic_verification_results/"
    if rel.startswith(prefix):
        rel = rel[len(prefix):]
    return os.path.splitext(rel)[0].replace("/", "::")

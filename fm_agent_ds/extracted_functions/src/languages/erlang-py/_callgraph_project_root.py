def _callgraph_project_root(proj_dir: str) -> str:
    """Resolve a pipeline workspace back to the original source-project root."""
    root = os.path.abspath(proj_dir)
    if not os.path.isdir(os.path.join(root, "extracted_functions")):
        return root

    parent = os.path.dirname(root)
    if parent == root:
        return root

    # The parent scan ignores fm_agent via _SKIP_DIRS, so only original project
    # sources qualify; extracted function files cannot trigger this redirect.
    if next(_iter_project_files(parent, {".erl"}), None) is not None:
        return parent
    return root

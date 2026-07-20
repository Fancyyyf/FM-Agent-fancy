# [SPEC]
# Unit: fm_agent/extracted_functions/src/languages/erlang-py/_callgraph_project_root.py
#
# _callgraph_project_root(proj_dir: str) -> str
#
# Pre-condition:
#   - proj_dir is a string representing a valid filesystem path to a project directory
#
# Post-condition:
#   - Returns the absolute, normalized path to the original source-project root directory
#   - If proj_dir does not contain an "extracted_functions" subdirectory, returns abspath(proj_dir)
#   - If proj_dir is the filesystem root (parent directory resolves to itself), returns abspath(proj_dir)
#   - If proj_dir contains "extracted_functions" and is not the filesystem root, and the parent directory contains at least one Erlang source file (.erl extension), returns the parent directory of proj_dir
#   - If proj_dir contains "extracted_functions" and is not the filesystem root, but the parent directory contains no Erlang source files, returns abspath(proj_dir)
# [SPEC]

# [INFO]
# _iter_project_files(dir: str, extensions: set[str]) -> Iterator[str]
#   Pre-condition: dir is a valid filesystem path to an existing directory; extensions is a non-empty set of file extensions each prefixed with a dot
#   Post-condition: Yields absolute paths to files under dir (recursively) whose extensions are in extensions, skipping any path that contains a directory whose name is in _SKIP_DIRS
# [INFO]

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

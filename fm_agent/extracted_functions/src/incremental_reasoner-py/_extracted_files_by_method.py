# [SPEC]
# Unit: fm_agent/extracted_functions/src/incremental_reasoner-py/_extracted_files_by_method.py
#
# _extracted_files_by_method(func_dir)
#
# Pre-condition:
#   - func_dir is a filesystem path (which may or may not be an existing directory)
#
# Post-condition:
#   - Returns a mutable dict-like mapping from string keys (function names) to lists of
#     absolute filesystem paths, each list containing one or more entries
#   - When func_dir is not an existing directory, returns an empty mapping (no keys present)
#   - When func_dir is an existing directory, every regular file reachable from func_dir
#     by recursive descent is indexed under one or two keys, using the file's basename
#     with its final dot-separated extension removed as the base identifier (the "stem"):
#     - The absolute path of the file is always appended to the list for the key equal to
#       the full stem
#     - Additionally, when the stem contains at least one "::" delimiter, the substring
#       after the last "::" (the bare method name) is used as a second key, and the same
#       absolute path is appended to the list for that key as well
#     - When the stem contains no "::" delimiter, only the stem itself is used as a key
#   - The order of absolute paths within each key's list reflects the order in which the
#     corresponding files were encountered during traversal
#   - Accessing a key not present in the mapping returns an empty list (rather than raising
#     an error), and mutating the returned list does not affect the mapping
# [SPEC]

def _extracted_files_by_method(func_dir):
    """``{key: [abs_path, ...]}`` for every extracted-function file under
    ``func_dir``, walked recursively. Each file is registered under BOTH keys so a
    caller can look it up whichever kind of name it holds:

      - its bare stem (``Flush``) — the regex change detector reports names
        without a class, so a bare name matches every same-named member;
      - its class-qualified identifier (``LocalStorage::Flush``) — scope ranking
        gets qualified names from codegraph spans, so this gives an exact match.

    A free function (``func_dir/foo.ext``) has identical stem and identifier, so it
    is registered once."""
    index = defaultdict(list)
    if not os.path.isdir(func_dir):
        return index
    for root, _dirs, fnames in os.walk(func_dir):
        for fn in fnames:
            abs_path = os.path.join(root, fn)
            # Flat layout: the filename stem is the full identifier, keeping any
            # "::" ("LocalStorage::Flush"). Register it under both the full
            # identifier and the bare tail ("Flush") so both codegraph's qualified
            # names and the regex detector's bare names resolve. (os.walk still
            # tolerates a legacy nested file, whose stem is already bare.)
            stem = fn[: fn.rfind(".")] if "." in fn else fn
            index[stem].append(abs_path)
            bare = stem.split("::")[-1]
            if bare != stem:
                index[bare].append(abs_path)
    return index

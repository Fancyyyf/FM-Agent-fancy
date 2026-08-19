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
            if _is_metadata_sidecar(fn):
                continue
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

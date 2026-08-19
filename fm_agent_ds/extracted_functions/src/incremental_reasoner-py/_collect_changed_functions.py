def _collect_changed_functions(proj_dir, old_commit_id, submodules=None):
    """
    Determine which functions changed between commit old_commit_id and the current working
    tree under proj_dir, so the incremental pipeline only re-analyzes what actually moved.

    Only source files whose extension is in EXT_TO_LANG are considered; test files (per
    _is_test_file), anything under the fm_agent work dir, and files outside submodules
    when a submodule scope is provided are ignored. For each candidate file, functions are
    extracted from both the old (old_commit_id) version and the current working-tree
    version, then compared by source text.

    Returns a dict mapping each changed file's absolute path to a dict with keys "added",
    "removed", and "modified", each a sorted list of function names. For every
    non-Erlang language that CodeGraph can index, both revisions are compared using
    its class-qualified identifiers. Erlang and CodeGraph-unavailable files retain
    the previous regex-based comparison. Files with no detectable function-level
    change are omitted. Raises subprocess.CalledProcessError if proj_dir is not a
    git repository or old_commit_id is not a valid commit.
    """
    # Pathspecs limiting git to recognized source-file extensions (e.g. "*.py", "*.cpp").
    pathspecs = [f"*.{ext}" for ext in EXT_TO_LANG]

    def _git(*args):
        return subprocess.run(
            ["git", "-C", proj_dir, *args],
            check=True,
            capture_output=True,
            text=True,
        ).stdout

    def _is_workspace_file(rel_path):
        norm = rel_path.replace("\\", "/")
        return norm == "fm_agent" or norm.startswith("fm_agent/")

    # Files that changed between old_commit_id and the working tree, plus untracked files
    # (new files absent from old_commit_id), then drop test and workspace files.
    changed = _git(
        "diff", "--name-only", old_commit_id, "--", *pathspecs
    ).splitlines()
    untracked = _git(
        "ls-files", "--others", "--exclude-standard", "--", *pathspecs
    ).splitlines()
    files = [
        f for f in dict.fromkeys(changed + untracked)
        if not _is_test_file(f) and not _is_workspace_file(f)
        and _is_under_submodules(f, submodules)
    ]

    # Erlang intentionally remains on its existing extraction path: its ELP
    # integration has different project and tooling requirements. Every other
    # changed language gets a CodeGraph comparison when both indexes are usable.
    file_languages = {
        rel_path: EXT_TO_LANG[rel_path.rsplit(".", 1)[-1]]
        for rel_path in files
        if "." in rel_path
        and rel_path.rsplit(".", 1)[-1] in EXT_TO_LANG
    }
    codegraph_file_languages = {
        rel_path: lang_key
        for rel_path, lang_key in file_languages.items()
        if lang_key != "erlang"
    }
    codegraph_langs = set(codegraph_file_languages.values())
    current_codegraph = (
        _codegraph_functions_by_file(proj_dir, codegraph_langs)
        if codegraph_langs else None
    )
    current_coverage = (
        _codegraph_legacy_coverage(
            proj_dir, current_codegraph, codegraph_file_languages
        )
        if current_codegraph is not None else None
    )
    baseline_codegraph = None
    baseline_coverage = None
    if current_codegraph is not None and codegraph_file_languages:
        baseline_result = _codegraph_functions_at_revision(
            proj_dir, old_commit_id, codegraph_file_languages
        )
        if baseline_result is not None:
            baseline_codegraph, baseline_coverage = baseline_result

    def _path_exists_in_commit(rel_path):
        """Return whether rel_path exists at old_commit_id without reading its contents."""
        return subprocess.run(
            ["git", "-C", proj_dir, "cat-file", "-e", f"{old_commit_id}:{rel_path}"],
            check=False,
            capture_output=True,
            text=True,
        ).returncode == 0

    def _funcs_from_commit(rel_path, lang_key, ext):
        """Extract {name: source} for the old_commit_id version of rel_path via a temp file."""
        text = _git("show", f"{old_commit_id}:{rel_path}")
        with tempfile.NamedTemporaryFile("w", suffix=f".{ext}", delete=False) as tmp:
            tmp.write(text)
            tmp_path = tmp.name
        try:
            return dict(extract_functions_from_file(tmp_path, lang_key))
        finally:
            os.unlink(tmp_path)

    result = {}
    for rel_path in files:
        ext = rel_path.rsplit(".", 1)[-1] if "." in rel_path else ""
        lang_key = EXT_TO_LANG.get(ext)
        if not lang_key:
            continue

        # Use CodeGraph for both revisions whenever it can index this non-Erlang
        # file. This keeps the comparison identity identical to the extracted
        # function filename (for example, ``LocalStorage::Flush``) and avoids
        # bare-name collisions between same-named C++ members.
        abs_path = os.path.abspath(os.path.join(proj_dir, rel_path))
        current_exists = os.path.exists(abs_path)
        old_exists = _path_exists_in_commit(rel_path)
        rel_key = _normalized_relative_path(proj_dir, rel_path)
        use_codegraph = (
            lang_key != "erlang"
            and current_codegraph is not None
            and baseline_codegraph is not None
            and (not current_exists or current_coverage.get(rel_key, False))
            and (not old_exists or baseline_coverage.get(rel_key, False))
        )

        if use_codegraph:
            new_funcs = current_codegraph.get(rel_key, {})
            old_funcs = baseline_codegraph.get(rel_key, {})
        else:
            if lang_key != "erlang" and codegraph_langs:
                logging.warning(
                    "CodeGraph could not provide both revisions for %s; using "
                    "legacy regex comparison.", rel_path,
                )
            new_funcs = (
                dict(extract_functions_from_file(abs_path, lang_key))
                if current_exists else {}
            )
            old_funcs = (
                _funcs_from_commit(rel_path, lang_key, ext) if old_exists else {}
            )

        added = sorted(n for n in new_funcs if n not in old_funcs)
        removed = sorted(n for n in old_funcs if n not in new_funcs)
        modified = sorted(
            n for n in new_funcs if n in old_funcs and new_funcs[n] != old_funcs[n]
        )
        if added or removed or modified:
            result[abs_path] = {
                "added": added,
                "removed": removed,
                "modified": modified,
            }

    return result

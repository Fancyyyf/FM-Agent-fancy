def _codegraph_functions_at_revision(proj_dir, revision, file_languages):
    """Index ``revision`` in a temporary worktree and return its functions.

    CodeGraph indexes real files rather than ``git show`` output. A linked
    worktree gives it an exact historical source tree without disturbing the
    caller's current checkout or its ``fm_agent`` artifacts.
    """
    parent_dir = tempfile.mkdtemp(prefix="fm_agent_incremental_base_")
    worktree_dir = os.path.join(parent_dir, "source")
    created = False
    try:
        try:
            subprocess.run(
                [
                    "git", "-C", proj_dir, "worktree", "add", "--detach",
                    "--quiet", worktree_dir, revision,
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            created = True
        except (OSError, subprocess.CalledProcessError) as exc:
            detail = getattr(exc, "stderr", "") or str(exc)
            logging.warning(
                "Could not create temporary worktree for CodeGraph baseline %s; "
                "falling back to legacy extraction: %s",
                revision, detail[:300],
            )
            return None

        try_codegraph_init(worktree_dir)
        lang_keys = set(file_languages.values())
        functions = _codegraph_functions_by_file(worktree_dir, lang_keys)
        if functions is None:
            logging.warning(
                "Could not build a CodeGraph index for baseline %s; falling back "
                "to legacy extraction.",
                revision,
            )
            return None
        coverage = _codegraph_legacy_coverage(
            worktree_dir, functions, file_languages
        )
        return functions, coverage
    finally:
        if created:
            subprocess.run(
                [
                    "git", "-C", proj_dir, "worktree", "remove", "--force",
                    worktree_dir,
                ],
                check=False,
                capture_output=True,
                text=True,
            )
        shutil.rmtree(parent_dir, ignore_errors=True)

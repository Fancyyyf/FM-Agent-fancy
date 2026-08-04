def _make_run_copy(proj_dir, run_dir):
    """Copy proj_dir (everything except .git) into a fresh ``run_dir``.

    Includes an existing ``fm_agent/`` workspace so a resumed pipeline finds the
    prior run's state. Any leftover run directory from an interrupted run is
    discarded first: the pristine sources always live in proj_dir, so the copy
    can be remade cleanly.
    """
    for stale in (run_dir, run_dir + ".tmp"):
        if os.path.exists(stale):
            shutil.rmtree(stale)
    tmp_dir = run_dir + ".tmp"
    shutil.copytree(
        proj_dir, tmp_dir,
        ignore=shutil.ignore_patterns(*_SKIP_DIRS),
        symlinks=True,
    )
    os.replace(tmp_dir, run_dir)

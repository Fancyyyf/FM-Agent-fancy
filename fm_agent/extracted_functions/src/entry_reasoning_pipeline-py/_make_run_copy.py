# [SPEC]
# Unit: fm_agent/extracted_functions/src/entry_reasoning_pipeline-py/_make_run_copy.py
#
# _make_run_copy(proj_dir, run_dir) -> None
#
# Pre-condition:
#   - proj_dir is an existing directory path
#
# Post-condition:
#   - proj_dir is never mutated
#   - run_dir holds a fresh recursive copy of proj_dir reflecting the state of proj_dir at call time, excluding entries whose names match a fixed, predefined set of skip patterns
#   - Directory symlinks present in proj_dir are preserved as symlinks in the copy
#   - Any pre-existing data at run_dir (e.g. a leftover directory from an interrupted prior invocation) is fully removed before the new copy is created
#   - The copy is atomically installed: no observer can see a partial or intermediate state at run_dir
# [SPEC]

# [INFO]
# (no callees)
# [INFO]

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

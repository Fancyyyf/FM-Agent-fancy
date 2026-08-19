#!/usr/bin/env python3
"""Probe for bug src--git-py--frozen_worktree.

Bug claim: in frozen_worktree()'s non-git fallback path, the call
    shutil.copytree(proj_dir, wt, ignore=shutil.ignore_patterns(*exclude), ...)
matches the basename of every exclude entry at ALL levels of the tree, so a
nested directory such as proj_dir/src/fm_agent/ is omitted from the snapshot.
The spec requires only the specific top-level directory named in `exclude`
(proj_dir/fm_agent) to be absent; the rest of the tree must be a faithful copy.

Probe: builds a fresh, NON-git fixture project inside a probe-owned temp dir:
    fixture_proj/
      README.txt                     (faithful-copy sanity check)
      fm_agent/phases.json           (real top-level workspace dir; must be excluded)
      src/fm_agent/old_results.json  (nested dir with the same basename; MUST be present)

Then calls frozen_worktree(proj_dir, exclude=('fm_agent',), copy_excluded=False)
through the same public import main.py uses, and inspects the snapshot.

  Buggy outcome  : snapshot lacks src/fm_agent/old_results.json -> CONFIRMED
  Spec outcome   : snapshot contains src/fm_agent/old_results.json -> NOT CONFIRMED

Self-contained: no network, no test framework, all fixtures/outputs live in
fresh temporary directories, which are removed at the end.
"""

import contextlib
import io
import os
import shutil
import sys
import tempfile

# Repo root = two levels above fm_agent/bug_validation/. Put it on sys.path so
# the package entry-point import used by main.py ("from src.git import ...")
# resolves when this probe is run from the repo root.
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

NESTED_CONTENT = '{"prior": "run"}'


def main():
    from src.git import frozen_worktree  # public import, as used by main.py

    work = tempfile.mkdtemp(prefix="probe_fwt_fixture_")
    snap_base = None
    try:
        proj_dir = os.path.join(work, "fixture_proj")
        nested_dir = os.path.join(proj_dir, "src", "fm_agent")
        top_ws_dir = os.path.join(proj_dir, "fm_agent")
        os.makedirs(nested_dir)
        os.makedirs(top_ws_dir)
        with open(os.path.join(nested_dir, "old_results.json"), "w") as f:
            f.write(NESTED_CONTENT)
        with open(os.path.join(top_ws_dir, "phases.json"), "w") as f:
            f.write("{}")
        with open(os.path.join(proj_dir, "README.txt"), "w") as f:
            f.write("fixture project")

        announcements = io.StringIO()
        with contextlib.redirect_stdout(announcements):
            # proj_dir has no .git anywhere up its tree -> non-git fallback path.
            with frozen_worktree(proj_dir, exclude=("fm_agent",), copy_excluded=False) as wt:
                snap_base = os.path.dirname(wt)
                nested_path = os.path.join(wt, "src", "fm_agent", "old_results.json")
                nested_present = os.path.isfile(nested_path)
                nested_content_ok = False
                if nested_present:
                    with open(nested_path) as f:
                        nested_content_ok = f.read() == NESTED_CONTENT
                toplevel_present = os.path.exists(os.path.join(wt, "fm_agent"))
                readme_present = os.path.isfile(os.path.join(wt, "README.txt"))

        # Spec oracle: only the top-level fm_agent directory is "the excluded
        # directory"; everything else (incl. src/fm_agent/) must be copied.
        spec_satisfied = (
            nested_present and nested_content_ok and readme_present and not toplevel_present
        )
        bug_reproduced = (not nested_present) and (not toplevel_present) and readme_present

        if bug_reproduced:
            print(
                "CONFIRMED - snapshot is missing nested src/fm_agent/old_results.json, "
                "which the spec requires to be present (only the top-level fm_agent "
                f"directory may be excluded). nested_present={nested_present}, "
                f"toplevel_fm_agent_present={toplevel_present}, readme_present={readme_present}"
            )
        elif spec_satisfied:
            print(
                "NOT CONFIRMED - snapshot contains the nested src/fm_agent/ directory "
                "exactly as the spec requires; only the top-level fm_agent was excluded."
            )
        else:
            print(
                f"NOT CONFIRMED - inconclusive snapshot state: nested_present={nested_present}, "
                f"nested_content_ok={nested_content_ok}, "
                f"toplevel_fm_agent_present={toplevel_present}, readme_present={readme_present}"
            )
    finally:
        # Remove everything the probe created, including the snapshot dir that
        # frozen_worktree deliberately retains on disk.
        if snap_base is not None and os.path.isdir(snap_base):
            shutil.rmtree(snap_base, ignore_errors=True)
        shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"ERROR: {type(exc).__name__}: {exc}")
        sys.exit(1)

"""Probe for bug src--incremental_reasoner-py--_extracted_files_by_method.

Spec claim (Condition B): "Every value list contains only absolute paths of
files that exist under func_dir at the time of the call."

Reported gap: the code computes ``abs_path = os.path.join(root, fn)`` where
``root`` comes from ``os.walk(func_dir)`` and never calls ``os.path.abspath``
/ ``os.path.realpath``. When ``func_dir`` itself is a RELATIVE path,
``os.walk`` yields relative roots and the produced "absolute" paths are in
fact relative, violating the specification.

Entry-point note: this is FM-Agent self-validation. Per the mandatory guard,
no FM-Agent workflow is started (no run_pipeline / run_incremental_pipeline /
main.py / CLI / OpenCode). The function under test is a private helper whose
only callers are internal incremental-pipeline helpers, so the probe imports
the repository package ``src`` (the package's public entry point module tree)
and exercises the helper directly with a temp-dir fixture. All runtime files
live under a fresh probe-owned temporary directory; the active repo and its
``fm_agent/`` directory are never used as the probe workspace.
"""

import os
import shutil
import sys
import tempfile

BUG_ID = "src--incremental_reasoner-py--_extracted_files_by_method"

REPO_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir, os.pardir)
)
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)


def main():
    try:
        from src.incremental_reasoner import _extracted_files_by_method
    except Exception as e:
        print(f"ERROR: failed to import package entry point 'src': {e}")
        return 1

    workdir = tempfile.mkdtemp(prefix="fm_probe_extracted_files_")
    old_cwd = os.getcwd()
    try:
        # Fixture: an extracted-functions dir under the probe-owned temp dir.
        func_dir_rel = os.path.join("extracted_funcs", "src--incremental_reasoner-py")
        fixture_dir = os.path.join(workdir, func_dir_rel)
        os.makedirs(fixture_dir)

        free_file = os.path.join(fixture_dir, "do_thing.py")  # free function
        qualified_file = os.path.join(fixture_dir, "LocalStorage::Flush.py")  # class-qualified
        sidecar_file = os.path.join(fixture_dir, "do_thing.info.json")  # metadata sidecar
        for path in (free_file, qualified_file, sidecar_file):
            with open(path, "w") as f:
                f.write("")

        # Run from inside the temp workspace so the RELATIVE func_dir resolves
        # under the probe-owned directory (never under the active repo).
        os.chdir(workdir)
        try:
            index = _extracted_files_by_method(func_dir_rel)
        finally:
            os.chdir(old_cwd)

        keys = sorted(index.keys())
        all_paths = [p for paths in index.values() for p in paths]

        print(f"DEBUG func_dir (relative input): {func_dir_rel}")
        print(f"DEBUG returned keys: {keys}")
        for p in all_paths:
            print(f"DEBUG path: {p} | os.path.isabs: {os.path.isabs(p)}")

        # Sanity gate: the fixture must actually be indexed, the sidecar must
        # be excluded, and both lookup keys must exist. Otherwise the result
        # would be meaningless and this run must be classified as an error.
        if not index or not all_paths:
            print("ERROR: fixture was not indexed at all (empty mapping returned)")
            return 1
        if any(k.endswith((".spec.json", ".info.json")) or "do_thing.info" in k for k in keys):
            print("ERROR: metadata sidecar leaked into the index; fixture broken")
            return 1
        if "do_thing" not in index or "LocalStorage::Flush" not in index or "Flush" not in index:
            print(f"ERROR: expected keys missing from index: {keys}")
            return 1

        # Oracle: the specification (Condition B) requires EVERY value-list
        # entry to be an absolute path. The buggy implementation returns
        # relative paths whenever func_dir is relative.
        expected = "all returned paths are absolute (os.path.isabs == True)"
        non_abs = [p for p in all_paths if not os.path.isabs(p)]
        bug_reproduced = len(non_abs) == len(all_paths) and len(all_paths) > 0

        if bug_reproduced:
            print(
                f"CONFIRMED — all {len(all_paths)} returned path(s) are RELATIVE "
                f"(e.g. {all_paths[0]!r}) although spec requires absolute paths | "
                f"expected: {expected}"
            )
            return 0
        if non_abs:
            print(
                f"CONFIRMED — {len(non_abs)}/{len(all_paths)} returned path(s) are RELATIVE "
                f"(e.g. {non_abs[0]!r}) although spec requires absolute paths | "
                f"expected: {expected}"
            )
            return 0
        print(
            f"NOT CONFIRMED — all {len(all_paths)} returned path(s) were absolute as the "
            f"spec requires; actual matched expected for relative func_dir input"
        )
        return 0
    except Exception as e:
        print(f"ERROR: probe crashed: {type(e).__name__}: {e}")
        return 1
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())

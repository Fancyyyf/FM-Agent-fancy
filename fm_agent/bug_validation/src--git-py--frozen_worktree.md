# Bug Report: frozen_worktree

**Source file:** `/tmp/fm_agent_wt_FM-Agent_6olacvfc/snapshot/fm_agent/extracted_functions/src/git-py/frozen_worktree.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

The function is used as a context manager and yields exactly one value: the path of an isolated "snapshot" directory located inside a freshly created temporary directory whose name embeds the basename of proj_dir, so concurrent snapshots of different projects are distinguishable and never share a location. The yielded directory is a faithful capture of proj_dir as of call time: it contains all of proj_dir's committed content plus all uncommitted modifications and untracked files, so the pipeline can run against it while later concurrent edits to proj_dir have no effect on the snapshot. When proj_dir is a git repository with at least one commit, proj_dir's real git index and working tree are never modified by building the snapshot, and none of the directory names in exclude appears in the snapshot's commit tree regardless of copy_excluded. When copy_excluded is true, every name in exclude that exists as a directory under proj_dir additionally exists inside the snapshot as a copy that preserves symlinks, making prior-run workspace artifacts available from disk; when copy_excluded is false, the excluded directories are entirely absent from the snapshot. When proj_dir is not a git repository with a commit, the snapshot is instead a full copy of the directory tree that preserves symlinks and likewise does not materialize the excluded directories. Before yielding, the function announces the snapshot location together with the command that removes it. When git operations fail while building the snapshot of a git repository, the underlying subprocess error propagates to the caller and no snapshot path is yielded. After the managed block exits, the snapshot directory is retained on disk and is never deleted by this function.

---

### Actual Behavior

The function is a generator. Upon first advancement (next()/send()), the following post-conditions hold at the yield point:

1. SNAPSHOT EXISTS: A directory `wt` exists at path `{base}/snapshot` where `base` is a freshly created temporary directory named `fm_agent_wt_{repo_name}_*`. The generator yields the absolute path string `wt`.

2. PROJ_DIR UNMODIFIED: The directory `proj_dir` (resolved to its absolute form) and its contents, including its git index and working tree, are unchanged. All git staging operations used a private GIT_INDEX_FILE located in `base`.

3. FAITHFUL SNAPSHOT: `wt` contains a complete snapshot of `proj_dir`'s state at function entry, including committed content, uncommitted tracked modifications, and untracked files.

4. GIT PATH (is_git=True, i.e., `git rev-parse --verify HEAD` succeeded):
   a. A new commit object (message 'fm_agent snapshot', parent HEAD) exists in proj_dir's git object store.
   b. A detached worktree is registered at `wt` pointing to that commit.
   c. The directories named in `exclude` are NOT part of the committed tree (removed via `git rm --cached` from the private index before write-tree).
   d. Cleanup requires `git -C {proj_dir} worktree remove --force {wt}`.

5. NON-GIT PATH (is_git=False, i.e., rev-parse raised CalledProcessError):
   a. `wt` is a plain recursive copy of `proj_dir` (symlinks preserved), created via shutil.copytree.
   b. Entries matching `exclude` patterns were omitted during the copy (shutil.ignore_patterns).
   c. Cleanup is `rm -rf {wt}`.

6. EXCLUDED-DIR COPY (copy_excluded=True): For each name in `exclude`, if `os.path.join(proj_dir, name)` is an existing directory and the corresponding path under `wt` does not already exist, a recursive copy (symlinks preserved) of that directory is placed at `os.path.join(wt, name)`. This makes prior-run artifacts physically readable inside the snapshot.

7. EXCLUDED-DIR SKIP (copy_excluded=False): No excluded directories are copied into `wt`; they remain absent from the snapshot.

8. PERSISTENCE: After the generator is exhausted (or the yielded value's consumer finishes), the snapshot directory `wt` and the temp base directory remain on disk. No automatic cleanup is performed.

9. OUTPUT: Two lines are printed to stdout identifying the snapshot path and the appropriate removal command.

10. EXCEPTION PROPAGATION: If any git subcommand other than `rev-parse --verify HEAD` fails (CalledProcessError), or if shutil.copytree / tempfile.mkdtemp / os operations raise, the exception propagates to the caller; no yield occurs and the generator raises. Partially created temp directories may remain on disk.

Formally:
   name  exclude: name  committed_tree(wt) 
  (copy_excluded  isdir(proj_dir/name)  isdir(wt/name)  content(wt/name) = content(proj_dir/name)) 
  (copy_excluded  exists(wt/name))
   state(proj_dir) = state_before(proj_dir)
   isdir(wt)  content(wt)  content(proj_dir) \ {exclude}
   yield_value = wt

---

## Code Evidence

Line 56: ignore=shutil.ignore_patterns(*exclude),

---

## Trigger Condition

In the non-git fallback path, shutil.ignore_patterns(*exclude) filters out any file or directory whose basename matches an exclude pattern at every level of the tree, not just the top-level directory identified by the exclude entry. The specification requires 'a full copy of the directory tree that preserves symlinks and likewise does not materialize the excluded directories', where 'the excluded directories' are the specific top-level paths named in the exclude parameter (e.g. proj_dir/fm_agent). A nested directory such as proj_dir/src/fm_agent/ is not one of 'the excluded directories' and must appear in the snapshot. The git path correctly handles this (git rm -r --cached -- fm_agent only removes the top-level path), but the non-git path over-excludes by matching the name at any depth. A concrete input: a non-git proj_dir containing src/fm_agent/old_results.json with exclude=('fm_agent',) and copy_excluded=False produces a snapshot missing that file, whereas the spec demands it be present.

---

## How to trigger the bug

In the non-git fallback path, `frozen_worktree()` copies `proj_dir` with
`shutil.copytree(proj_dir, wt, ignore=shutil.ignore_patterns(*exclude), symlinks=True)`
(`src/git.py`, line 108; cited as line 56 / line 62 in the extracted-function view).
`shutil.ignore_patterns("fm_agent")` returns an ignore callable that fnmatch-tests the
**basename of every entry at every depth** of the tree, so any file or directory simply
named `fm_agent` anywhere under `proj_dir` is dropped from the copy. The specification
excludes only "the excluded directories" — the specific top-level paths named in
`exclude` (here `proj_dir/fm_agent`) — and requires the rest of the tree to be a
faithful full copy. A nested directory `proj_dir/src/fm_agent/` is not one of "the
excluded directories" and must appear in the snapshot; the buggy code omits it instead.
(`copy_excluded=False` is used, so the post-copy re-materialization loop is skipped and
cannot mask the over-exclusion.) The git path does not suffer this defect because
`git rm -r --cached -- fm_agent` only matches the top-level path.

### Inputs

| Parameter | Value |
|-----------|-------|
| `proj_dir` | Fresh non-git temp dir containing `README.txt`, `fm_agent/phases.json`, and `src/fm_agent/old_results.json` |
| `exclude` | `("fm_agent",)` |
| `copy_excluded` | `False` |

### Expected (spec-correct) Output

`os.path.isfile(os.path.join(wt, "src", "fm_agent", "old_results.json"))` returns `True` (nested directory preserved; only the top-level `proj_dir/fm_agent` absent from the snapshot).

### Actual (buggy) Output

`os.path.isfile(os.path.join(wt, "src", "fm_agent", "old_results.json"))` returns `False` — the nested `src/fm_agent/` subtree is silently dropped from the snapshot.

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import os
import tempfile
from src.git import frozen_worktree  # same public import used by main.py

proj = tempfile.mkdtemp(prefix="demo_proj_")  # NOT a git repository
os.makedirs(os.path.join(proj, "src", "fm_agent"))
os.makedirs(os.path.join(proj, "fm_agent"))
with open(os.path.join(proj, "src", "fm_agent", "old_results.json"), "w") as f:
    f.write("{}")
with open(os.path.join(proj, "fm_agent", "phases.json"), "w") as f:
    f.write("{}")
with open(os.path.join(proj, "README.txt"), "w") as f:
    f.write("demo")

with frozen_worktree(proj, exclude=("fm_agent",), copy_excluded=False) as wt:
    print(os.path.isfile(os.path.join(wt, "src", "fm_agent", "old_results.json")))
# actual (buggy) output: False
# expected (correct) output: True
```

---

## Probe Script

```python
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
```

### Probe Output

```
CONFIRMED - snapshot is missing nested src/fm_agent/old_results.json, which the spec requires to be present (only the top-level fm_agent directory may be excluded). nested_present=False, toplevel_fm_agent_present=False, readme_present=True
```

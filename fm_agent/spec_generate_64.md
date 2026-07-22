# Generate Function Specification

A modification has been applied to a codebase to achieve the developer intent below, adding a function that has no behavioral specification yet. Generate its specification from scratch.

- Function fully-qualified name: `src::git-py::frozen_worktree::_git` (language: `python`).
- Comment prefix for this language: `#`.
- Known callees of this function: run.

## Developer intent

# Incremental self-validation intent

Validate all behavioral and correctness impacts introduced between the recorded
FM-Agent baseline and the current checked-out main-derived revision. Regenerate
specifications for changed or relevant functions and verify affected callers.
Pay particular attention to file readiness, incremental reasoning, CLI backend,
codegraph integration, tracing, environment checks, and pipeline setup changes.
Do not modify project source files; write validation artifacts only under the
FM-Agent workspace.

## Function source

```python
def _git(*args, **kwargs):
        return subprocess.run(
            ["git", "-C", proj_dir, *args],
            check=True, capture_output=True, text=True, **kwargs,
        ).stdout.strip()
```

## Specs of this function's callers

### src::git-py::frozen_worktree

# [SPEC]
# Unit: src/git.py
#
# frozen_worktree(proj_dir, exclude=("fm_agent",), copy_excluded=True) -> yields str
#
# Pre-condition:
#   - proj_dir is a filesystem path; it may or may not be a git repository and may
#     or may not contain commits
#   - exclude is an iterable of strings naming subdirectories of proj_dir to keep out
#     of the git snapshot commit
#   - copy_excluded is a boolean
#
# Post-condition:
#   - A new, unique temporary directory is created under the system tempdir. Its name
#     begins with "fm_agent_wt_" followed by the basename of proj_dir.
#   - When proj_dir is a git repository with a reachable HEAD commit:
#       - A private git index (GIT_INDEX_FILE) is used so that proj_dir's real index
#         and working tree are never modified.
#       - The snapshot commit captures the full state of proj_dir at entry time:
#         HEAD tree + all tracked modifications + all untracked files, with every
#         path in exclude removed from the snapshot commit tree.
#       - That commit becomes a detached git worktree checked out inside the tempdir
#         at a "snapshot" subdirectory. The yielded path is this snapshot subdirectory.
#       - If copy_excluded is truthy: for each name in exclude, if the corresponding
#         subdirectory exists in proj_dir and does not already exist at the same
#         relative path in the snapshot worktree, that subdirectory is recursively
#         copied (with symlinks preserved) into the snapshot worktree.
#   - When proj_dir is NOT a git repository or has no reachable HEAD:
#       - A plain recursive directory copy is performed from proj_dir into the
#         snapshot subdirectory, using copytree with each name in exclude passed as
#         an ignore pattern and with symlinks preserved. The yielded path is the
#         snapshot subdirectory.
#       - If copy_excluded is truthy: excluded subdirectories are copied into the
#         snapshot worktree under the same conditions as the git-path case.
#   - The absolute path of the snapshot worktree is printed to stdout along with
#     platform-appropriate removal instructions referencing either "git worktree
#     remove" (git path) or "rm -rf" (non-git path).
#   - The snapshot worktree and its parent temporary directory persist after the
#     context manager exits; automatic cleanup is not performed.
#   - If any git or filesystem operation fails (e.g. git command returns non-zero,
#     directory is not writable), the corresponding subprocess.CalledProcessError or
#     OSError propagates to the caller.
# [SPEC]

## Steps

1. Read `fm_agent/spec_prompts/system_prompt.md` for the exact [SPEC]/[INFO] format rules used by this project.
2. Produce the COMPLETE [SPEC] block describing this function's behavior — the `[SPEC]` ... `[SPEC]` block only, markers included, every line prefixed with `#`, and NO source code.
3. Because this function has callees, also produce an [INFO] block recording the expected behavioral spec of each callee it depends on (the `[INFO]` ... `[INFO]` block only, markers included, every line prefixed with `#`), and list the names of the callees you recorded.
4. Write your answer to `fm_agent/spec_generate_64.json` as a JSON object with keys:
   - "spec_updated": boolean — true when you produced a [SPEC] block.
   - "new_spec": string — the full [SPEC] block.
   - "info_updated": boolean — true when you produced an [INFO] block.
   - "new_info": string — the full [INFO] block, or "" if none.
   - "updated_callees": array of callee name strings recorded in [INFO], or [].
   Write ONLY that JSON file; do not modify any other project files.

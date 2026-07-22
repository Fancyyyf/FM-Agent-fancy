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

# [INFO]
# os.path.abspath(proj_dir) -> str
#   Pre-condition: proj_dir is a string path
#   Post-condition: returns the absolute, normalized equivalent of proj_dir
# [SPLIT]
# tempfile.mkdtemp(prefix=str) -> str
#   Pre-condition: none (system tempdir exists and is writable)
#   Post-condition: creates a new unique empty directory in the system temporary
#     directory and returns its absolute path; raises OSError if creation fails
# [SPLIT]
# subprocess.run(["git", "-C", proj_dir, ...], check=True, capture_output=True, text=True) -> CompletedProcess
#   Pre-condition: git is installed and accessible; proj_dir exists
#   Post-condition: executes the git command in proj_dir, captures stdout as a string.
#     If the command exits with a non-zero status, raises CalledProcessError with the
#     return code, stdout, and stderr.
# [SPLIT]
# _git(*args, **kwargs) -> str
#   Pre-condition: proj_dir is a directory path in enclosing scope; git is installed
#     and accessible; *args are zero or more strings forming the git subcommand and
#     its operands; **kwargs are zero or more keyword arguments forwarded to the
#     subprocess invocation, merged with defaults (check=True, capture_output=True,
#     text=True).
#   Post-condition: executes "git -C proj_dir *args" as a child process; stdout
#     and stderr are captured and do not appear on the parent's streams. If the
#     process exits with a non-zero code, raises subprocess.CalledProcessError
#     with the returncode, stdout, stderr, and cmd. On exit code zero, returns the
#     captured stdout with all leading and trailing whitespace removed. The child
#     inherits the parent's environment, modifiable via an env keyword argument.
# [SPLIT]
# shutil.copytree(src, dst, ignore=callable, symlinks=True) -> str
#   Pre-condition: src exists and is a directory; dst does not exist
#   Post-condition: recursively copies src to dst preserving symlinks (not following
#     them); entries matching the ignore callable are excluded from the copy. Returns dst.
#     Raises OSError if src is not a directory or dst already exists.
# [SPLIT]
# logging.info(fmt, *args)
#   Pre-condition: logging is configured with at least one handler at INFO level or above
#   Post-condition: the formatted message is emitted via all configured handlers at INFO
#     severity; no exception is raised on logging failure with default configuration
# [SPLIT]
# print(message)
#   Pre-condition: stdout is open and writable
#   Post-condition: the string representation of message followed by a newline is written
#     to stdout; returns None
# [INFO]

def frozen_worktree(proj_dir, exclude=("fm_agent",), copy_excluded=True):
    """Freeze proj_dir's current working tree into an isolated git worktree.

    Captures committed state PLUS uncommitted edits and untracked files, so the
    yielded copy is a faithful snapshot of proj_dir at entry time. Concurrent
    edits to proj_dir afterwards do not affect the snapshot, letting the pipeline
    run against a stable copy.

    The snapshot is built through a private index (GIT_INDEX_FILE), so proj_dir's
    real index and working tree are never touched. Falls back to a plain directory
    copy when proj_dir is not a git repository with a commit. The snapshot folder
    is left in place after the run (including its fm_agent/ outputs); its path is
    logged so it can be inspected or cleaned up manually.

    The `exclude` dirs (the FM-Agent's own workspace) are always kept out of the
    git snapshot commit so it stays clean. When `copy_excluded` is set, they are
    then copied into the worktree as-is. Incremental mode needs the previous run's
    fm_agent/ results to detect a prior full run, and those results are typically
    gitignored, hence absent from the snapshot commit. A full run discards any
    prior fm_agent/, so it passes copy_excluded=False to skip the copy.
    """
    proj_dir = os.path.abspath(proj_dir)
    # Include the repo name in the temp dir so concurrent runs across different
    # repos are distinguishable (e.g. /tmp/fm_agent_wt_myrepo_a3k9d2/snapshot).
    repo_name = os.path.basename(proj_dir.rstrip(os.sep)) or "repo"
    base = tempfile.mkdtemp(prefix=f"fm_agent_wt_{repo_name}_")
    wt = os.path.join(base, "snapshot")

    def _git(*args, **kwargs):
        return subprocess.run(
            ["git", "-C", proj_dir, *args],
            check=True, capture_output=True, text=True, **kwargs,
        ).stdout.strip()

    is_git = False
    try:
        _git("rev-parse", "--verify", "HEAD")
        is_git = True
    except subprocess.CalledProcessError:
        pass

    if is_git:
        env = dict(os.environ, GIT_INDEX_FILE=os.path.join(base, "index"))
        _git("read-tree", "HEAD", env=env)
        # Stage the full working tree (tracked edits + untracked files). Using a
        # bare `git add -A` lets git silently skip gitignored paths; passing the
        # workspace dirs as :(exclude) pathspecs instead errors out when a repo
        # already gitignores them ("paths are ignored ... use -f"). Drop the
        # workspace dirs from the private index afterwards to cover repos that do
        # NOT gitignore them.
        _git("add", "-A", env=env)
        if exclude:
            _git("rm", "-r", "--cached", "--quiet", "--ignore-unmatch", "--",
                 *exclude, env=env)
        tree = _git("write-tree", env=env)
        snap = _git("commit-tree", tree, "-p", "HEAD", "-m", "fm_agent snapshot")
        _git("worktree", "add", "--detach", wt, snap)
    else:
        logging.info("frozen_worktree: %s is not a git repo; copying instead.", proj_dir)
        shutil.copytree(
            proj_dir, wt,
            ignore=shutil.ignore_patterns(*exclude),
            symlinks=True,
        )

    # Copy the excluded workspace dirs (e.g. fm_agent/ with a prior full run's
    # phases.json and extracted_functions) into the snapshot. They were kept out
    # of the git commit, but incremental mode reads them from disk to compare
    # against, so the snapshot must physically contain them.
    if copy_excluded:
        for name in exclude:
            src = os.path.join(proj_dir, name)
            dst = os.path.join(wt, name)
            if os.path.isdir(src) and not os.path.exists(dst):
                shutil.copytree(src, dst, symlinks=True)

    print(f"[Pipeline] Snapshot created at: {wt}")
    print(f"[Pipeline] Snapshot is kept after the run. "
          f"Remove with: git -C {proj_dir} worktree remove --force {wt}"
          if is_git else
          f"[Pipeline] Snapshot is kept after the run. Remove with: rm -rf {wt}")
    yield wt

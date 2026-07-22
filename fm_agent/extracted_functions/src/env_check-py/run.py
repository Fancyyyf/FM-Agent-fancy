# [SPEC]
# Unit: src/env_check-py/run.py
#
# run(proj_dir: str, config) -> bool
#
# Pre-condition:
#   - proj_dir is a directory path that exists on the filesystem.
#   - config provides access to an LLM API key (the specific accessor used is LLM_API_KEY).
#
# Post-condition:
#   - Returns True when any of the following holds: (a) all environment checks pass with no
#     warnings, (b) one or more checks fail but the session is non-interactive, (c) one or
#     more checks fail in an interactive session and the user chooses to proceed ('p'), or
#     (d) one or more checks fail in an interactive session and the user chooses to permanently
#     ignore the failing checks ('i').
#   - Returns False only when one or more checks fail in an interactive session and the user
#     chooses to quit ('q'). No persistent state is modified in this case.
#   - When the user chooses 'i', the union of all previously ignored check IDs and the IDs of
#     all currently failing checks is persisted to proj_dir/fm_agent/.env_check_memory, causing
#     all such checks to be skipped on subsequent calls.
#   - Checks whose ID appears in the persisted ignore set (loaded at the start of the call)
#     are skipped entirely: their check function is not invoked.
#   - Each failing check produces a warning logged via logging.warning in the format
#     "[!] <label>: <message>" where label identifies the check and message is the
#     reason for failure.
#   - The directory proj_dir/fm_agent/ is created if it does not already exist.
#   - In interactive mode, the function blocks on user input and does not return until a
#     valid choice (p, i, or q) is entered.
# [SPEC]

# [INFO]
# _load_ignored(work_dir: str) -> set[str]
#   Pre-condition: work_dir is a directory path that exists.
#   Post-condition: Returns the set of check IDs previously persisted as ignored.
#     Returns an empty set when no ignores have been persisted.
# [SPLIT]
# _check_llm_api_key(config) -> (bool, str | None)
#   Pre-condition: config provides access to LLM_API_KEY.
#   Post-condition: Returns (True, None) when the LLM API key is present and non-empty.
#     Returns (False, str) with an error message when the key is missing or empty.
# [SPLIT]
# _check_oh_my_openagent() -> (bool, str | None)
#   Pre-condition: None.
#   Post-condition: Returns (True, None) when oh-my-openagent is available and executable
#     via bunx. Returns (False, str) with a fixed error message when it is not available
#     or the check times out. Does not raise exceptions.
# [SPLIT]
# _check_comment_checker() -> (bool, str | None)
#   Pre-condition: None.
#   Post-condition: Returns (True, None) when the oh-my-openagent comment-checker hook is
#     disabled. Returns (False, str) with an error message when it is still enabled.
# [SPLIT]
# _check_codegraph_version(config) -> (bool, str | None)
#   Pre-condition: config provides access to a codegraph version string via settings.codegraph.version and a binary directory path via settings.codegraph.bin_dir.
#   Post-condition: Returns (True, None) when the configured version (after stripping whitespace and leading "v") is empty.
#     Otherwise, tries to obtain the installed version by executing the binary with --version.
#     Returns (False, message) when the version cannot be obtained (binary missing/not executable/timeout), mentioning the binary directory and instructing to re-run ./install.sh.
#     Returns (False, message) when the obtained version does not equal the pinned version (after stripping whitespace and leading "v"), stating both versions and instructing to re-run ./install.sh.
#     Returns (True, None) when versions match.
#     Never raises an exception.
# [SPLIT]
# is_interactive() -> bool
#   Pre-condition: None.
#   Post-condition: Returns True when the current process is attached to an interactive
#     terminal (allowing user input via stdin); returns False otherwise.
# [SPLIT]
# _save_ignored(work_dir: str, ignored: set[str]) -> None
#   Pre-condition: work_dir is a directory path that exists; ignored is a set of check ID
#     strings to persist.
#   Post-condition: Persists the set of ignored check IDs such that a subsequent call to
#     _load_ignored(work_dir) returns the same set.
# [INFO]

def run(proj_dir, config):
    """Run all env checks.  Return True to proceed, False to abort."""
    work_dir = os.path.join(proj_dir, "fm_agent")
    os.makedirs(work_dir, exist_ok=True)
    ignored = _load_ignored(work_dir)

    checks = [
        ("llm_key", "LLM API Key configured",
         lambda: _check_llm_api_key(config)),
        ("oh-my-openagent", "oh-my-openagent installed",
         _check_oh_my_openagent),
        ("comment-checker-disabled", "comment-checker hook disabled",
         _check_comment_checker),
        ("codegraph-version", "codegraph pinned build installed",
         lambda: _check_codegraph_version(config)),
    ]

    warnings = []
    for check_id, label, fn in checks:
        if check_id in ignored:
            continue
        ok, msg = fn()
        if not ok:
            warnings.append((check_id, label, msg))

    if not warnings:
        return True

    lines = [
        "",
        "=" * 62,
        "  FM-Agent environment check — potential issues found:",
        "=" * 62,
    ]
    for _, label, msg in warnings:
        lines.append(f"  [!] {label}: {msg}")
    lines.append("=" * 62)
    lines.append("")
    for line in lines:
        logging.warning(line)

    if not is_interactive():
        logging.warning(
            "Non-interactive session — proceeding with warnings. "
            "Fix the issues above for best results."
        )
        return True

    print("\n".join(lines))
    print("These issues may cause FM-Agent to fail or produce wrong results.\n")
    print("  [p] proceed anyway (warn again next run)")
    print("  [i] ignore — don't warn again (saved to fm_agent/.env_check_memory)")
    print("  [q] quit — fix the issues first\n")

    while True:
        choice = input("Your choice [p/i/q]: ").strip().lower()
        if choice == "p":
            return True
        elif choice == "i":
            _save_ignored(work_dir, ignored | {cid for cid, _, _ in warnings})
            return True
        elif choice == "q":
            print("\n[FM-Agent] Aborted. Fix the issues listed above and run again.\n")
            return False
        else:
            print("Invalid choice — enter p, i, or q.")

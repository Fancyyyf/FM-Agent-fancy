def run(proj_dir, config):
    """Run all env checks.  Return True to proceed, False to abort."""
    from src.cli_backend import is_cli_backend_enabled

    work_dir = os.path.join(proj_dir, "fm_agent")
    os.makedirs(work_dir, exist_ok=True)
    ignored = _load_ignored(work_dir)

    checks = [
        ("codegraph-version", "codegraph pinned build installed",
         lambda: _check_codegraph_version(config)),
    ]
    if not is_cli_backend_enabled():
        checks[:0] = [
            ("llm_key", "LLM API Key configured",
             lambda: _check_llm_api_key(config)),
            ("oh-my-openagent", "oh-my-openagent installed",
             _check_oh_my_openagent),
            ("comment-checker-disabled", "comment-checker hook disabled",
             _check_comment_checker),
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

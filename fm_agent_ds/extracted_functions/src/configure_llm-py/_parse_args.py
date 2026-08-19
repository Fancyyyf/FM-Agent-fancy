def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Configure FM-Agent's LLM provider or update individual LLM settings."
    )
    subcommands = parser.add_subparsers(dest="command")
    set_parser = subcommands.add_parser(
        "set",
        help="update only the specified non-secret [llm] settings in fm-agent.toml",
    )
    set_parser.add_argument("--name", help="LLM model ID (LLM_MODEL)")
    set_parser.add_argument("--provider", help="OpenCode provider ID (OPENCODE_MODEL_PROVIDER)")
    set_parser.add_argument("--base-url", dest="base_url", help="API base URL (LLM_API_BASE_URL)")
    set_parser.add_argument(
        "--backend",
        choices=_BACKENDS,
        help="model backend: opencode, auto, codex-cli, or claude-cli",
    )
    set_parser.add_argument(
        "--effort",
        choices=_EFFORTS,
        help="reasoning effort: empty, low, medium, or high",
    )
    set_parser.add_argument(
        "--api-style",
        dest="api_style",
        choices=("openai", "anthropic"),
        help="OpenCode adapter API style",
    )
    set_parser.add_argument(
        "--yes",
        action="store_true",
        help="write without asking for confirmation",
    )
    args = parser.parse_args(argv)
    if args.command == "set":
        updates = {
            key: getattr(args, key)
            for key in _LLM_TOML_KEYS
            if getattr(args, key) is not None
        }
        if not updates:
            set_parser.error("provide at least one setting to update")
        args.updates = updates
    return args

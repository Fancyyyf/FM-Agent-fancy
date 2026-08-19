def main(argv: list[str] | None = None) -> int:
    try:
        args = _parse_args(argv)
        project_root = Path(__file__).resolve().parents[1]
        if args.command == "set":
            return run_llm_settings_update(
                project_root,
                args.updates,
                assume_yes=args.yes,
            )
        return run_wizard(project_root)
    except KeyboardInterrupt:
        print("\nAborted.")
        return 1
    except ConfigWizardError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2

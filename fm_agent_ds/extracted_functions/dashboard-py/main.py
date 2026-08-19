def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("proj_dir",
                    help=("Either a target codebase (monitors <proj_dir>/fm_agent/) "
                          "or a workspace directly (any dir containing a trace/ subdir)"))
    ap.add_argument("--refresh", type=float, default=1.5, help="Refresh seconds (default 1.5)")
    args = ap.parse_args()

    state = State(args.proj_dir)
    if not state.trace_dir.exists():
        print(f"trace dir not found: {state.trace_dir}", file=sys.stderr)
        print("Has the pipeline started yet? (waiting…)", file=sys.stderr)

    console = Console()
    with Live(console=console, refresh_per_second=max(1.0, 1.0 / args.refresh),
              screen=True) as live:
        try:
            while True:
                state.tail_events()
                state.tail_opencode()
                state.scan_bugs()
                live.update(build_layout(state))
                time.sleep(args.refresh)
        except KeyboardInterrupt:
            pass

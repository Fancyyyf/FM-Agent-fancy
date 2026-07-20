# [SPEC]
# Unit: fm_agent/extracted_functions/dashboard-py/main.py
#
# main() -> None
#
# Pre-condition:
#   - sys.argv contains at minimum one argument: a filesystem path to either a
#     project directory (with an fm_agent/ subdirectory) or a workspace directory
#     (with a trace/ subdirectory).
#   - sys.argv may contain an optional --refresh flag followed by a float value
#     greater than zero.
#
# Post-condition:
#   - If the trace directory expected under the project directory does not exist,
#     a diagnostic message and a waiting hint are written to stderr; execution
#     continues regardless.
#   - Enters an infinite loop. On each iteration:
#       - The dashboard state is refreshed with the latest trace events, OpenCode
#         trace data, and bug validation results from the filesystem.
#       - A full-screen terminal UI is rendered showing the current aggregated
#         dashboard state, refreshed at a rate no slower than once per second
#         and no faster than the configured refresh interval.
#       - The loop sleeps for the configured refresh interval (default 1.5
#         seconds) after each render.
#   - On KeyboardInterrupt, the loop terminates and the function returns without
#     propagating the exception.
# [SPEC]

# [INFO]
# State(proj_dir: str) -> State
#   Pre-condition: proj_dir is a non-empty string representing a filesystem path.
#   Post-condition: Returns a State instance initialized with the trace directory
#     resolved from the given path.
# [SPLIT]
# State.tail_events(self) -> None
#   Pre-condition: self was initialized with a project directory.
#   Post-condition: Reads any new entries from the trace events file since the
#     last call and appends them to the State's internal event list.
# [SPLIT]
# State.tail_opencode(self) -> None
#   Pre-condition: self was initialized with a project directory.
#   Post-condition: Reads any new OpenCode trace data since the last call and
#     updates the State's internal metrics accordingly.
# [SPLIT]
# State.scan_bugs(self) -> None
#   Pre-condition: self was initialized with a project directory.
#   Post-condition: Scans the bug validation directory for new or updated bug
#     reports since the last call and updates the State's internal bug report
#     collection.
# [SPLIT]
# build_layout(state: State) -> RenderableType
#   Pre-condition: state is a State object populated with current trace and bug
#     data.
#   Post-condition: Returns a Rich renderable that, when displayed, produces a
#     full terminal screen layout whose content reflects the data contained in
#     state at the time of the call.
# [INFO]

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

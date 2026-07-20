# [SPEC]
# Unit: fm_agent/extracted_functions/dashboard-py/build_layout.py
#
# build_layout(state: State) -> RenderableType
#
# Pre-condition:
#   - state is a State instance whose aggregated fields (stage counts, token
#     totals, cache statistics, LLM status history, recent events, bug
#     validation counts) reflect the latest ingested trace data
#
# Post-condition:
#   - Returns a Rich Layout renderable that, when rendered to a terminal,
#     produces a full-screen dashboard partitioned into vertically stacked
#     regions: header, top, mid, and footer
#   - The header region contains run identification information derived
#     from state
#   - The top region is horizontally split into a pipeline stage progress
#     panel (ratio 3) and a right column containing a prompt-cache panel
#     (ratio 2) stacked above a bug-validation summary panel (ratio 1)
#   - The mid region is horizontally split into a token-usage statistics
#     panel (ratio 3) and an LLM call status panel (ratio 2)
#   - The footer region displays the most recent trace events in
#     chronological order
#   - Every panel's rendered content reflects the data in state at the
#     moment of the call
#   - Region heights are computed from the number of data rows each panel
#     is expected to render, not from fixed absolute sizes
# [SPEC]

# [INFO]
# render_header(state: State) -> RenderableType
#   Pre-condition: state is a State instance with project path and run
#     identification attributes populated
#   Post-condition: Returns a renderable displaying the dashboard title
#     and project identification
# [SPLIT]
# render_stages(state: State) -> RenderableType
#   Pre-condition: state.stage_counts and state.stage_active contain
#     pipeline stage status tallies aggregated from ingested events
#   Post-condition: Returns a renderable displaying each pipeline stage
#     name with its count of completed, in-progress, and error events
# [SPLIT]
# render_cache(state: State) -> RenderableType
#   Pre-condition: state.cache_window contains recent (cache_read,
#     total_input) tuples from ingested trace data
#   Post-condition: Returns a renderable displaying prompt-cache hit
#     statistics derived from the cached window of recent reads
# [SPLIT]
# render_bugs(state: State) -> RenderableType
#   Pre-condition: state.bugs_confirmed and state.bugs_not_confirmed
#     reflect bug-validation verdicts from ingested trace data
#   Post-condition: Returns a renderable displaying confirmed and
#     unconfirmed bug counts
# [SPLIT]
# render_tokens(state: State) -> RenderableType
#   Pre-condition: state.totals and state.opencode_token_totals contain
#     token-usage tallies aggregated from ingested trace events
#   Post-condition: Returns a renderable displaying token consumption
#     broken down by source (verification, OpenCode) and a combined total
# [SPLIT]
# render_llm_status(state: State) -> RenderableType
#   Pre-condition: state.llm_statuses contains recent LLM call status
#     records from ingested trace data
#   Post-condition: Returns a renderable displaying the most recent
#     LLM call outcomes with their associated stage and status
# [SPLIT]
# render_recent(state: State) -> RenderableType
#   Pre-condition: state.recent_events contains recent (time, stage,
#     status, summary) tuples from ingested events
#   Post-condition: Returns a renderable displaying a chronological
#     log of the most recent trace events
# [INFO]

def build_layout(state):
    # Heights are computed to exactly fit content. A Rich Table renders as
    #   2 (top+bottom edge) + 1 (header) + 1 (header-rule) + N (rows)
    # and Panel adds 2 more border lines, so a Table-in-Panel = N + 6 lines.
    # A Text-in-Panel = N_lines + 2. Small panels (cache, bugs) are Align-centered
    # so the spare height goes evenly above/below instead of bunching at the top.
    stages_h = len(STAGES) + 6                 # 5 + 6 = 11
    tokens_h = 3 + 6                           # 3 rows ("verification", "opencode", "TOTAL") + 6 = 9

    layout = Layout()
    layout.split_column(
        Layout(render_header(state), name="header", size=3),
        Layout(name="top", size=stages_h),
        Layout(name="mid", size=tokens_h),
        Layout(render_recent(state), name="footer"),
    )
    layout["top"].split_row(
        Layout(render_stages(state), name="stages", ratio=3),
        Layout(name="top_right", ratio=2),
    )
    layout["top"]["top_right"].split_column(
        Layout(render_cache(state), name="cache", ratio=2),
        Layout(render_bugs(state), name="bugs", ratio=1),
    )
    layout["mid"].split_row(
        Layout(render_tokens(state), name="tokens", ratio=3),
        Layout(render_llm_status(state), name="llm", ratio=2),
    )
    return layout

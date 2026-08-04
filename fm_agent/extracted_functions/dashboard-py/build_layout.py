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

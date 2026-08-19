def _build_domain_context_regen_prompt(phase_source_files, phase_cleanup=None):
    """Compose the instruction telling the agent to regenerate the per-phase
    domain-context types files for phases whose source-file list changed.

    ``phase_source_files`` maps a changed phase's number to its CURRENT source
    files in phases.json (the caller guarantees the list is non-empty). For each
    phase the agent rewrites phase_NN_types.txt from scratch from those files'
    real types/structs/invariants, so previously force-added or deduplicated files
    are reflected without any mechanical text surgery.
    """
    lines = []
    for phase_num in sorted(phase_source_files):
        file_str = ", ".join(phase_source_files[phase_num])
        lines.append(
            f"  - phase {phase_num}: REGENERATE phase_{phase_num:02d}_types.txt from "
            f"scratch. Its source_files are now: {file_str}. READ them in the project "
            f"and write the real types/structs/invariants they define. Do not leave "
            f"the file empty or invent content."
        )
    changes_text = "\n".join(lines)
    if not changes_text:
        changes_text = (
            "  - No phase_NN_types.txt files need regeneration; only update "
            "engine_overview.txt if cleanup made its phase references stale."
        )
    phase_cleanup = phase_cleanup or {}
    removed_phases = [
        p for p in phase_cleanup.get("removed_phases", [])
        if p is not None
    ]
    renumbered = phase_cleanup.get("renumbered", {})
    renumbered_changes = {
        old: new for old, new in renumbered.items()
        if old is not None and new is not None and old != new
    }

    overview_rule = (
        "- engine_overview.txt does not need updating; touch it only if it "
        "explicitly names a phase number that changed."
    )
    if removed_phases or renumbered_changes:
        cleanup_lines = []
        if removed_phases:
            cleanup_lines.append(
                "removed old phase number(s): "
                + ", ".join(str(p) for p in sorted(removed_phases))
            )
        if renumbered_changes:
            cleanup_lines.append(
                "renumbered surviving phase(s): "
                + ", ".join(
                    f"{old} -> {new}"
                    for old, new in sorted(renumbered_changes.items())
                )
            )
        overview_rule = (
            "- Review engine_overview.txt and update any phase-numbered references "
            "so they match the final phases.json after cleanup ("
            + "; ".join(cleanup_lines)
            + ")."
        )

    return (
        "Regenerate per-phase domain-context "
        "files under fm_agent/spec_prompts/domain_context/ (named phase_NN_types.txt) so each reflects its phase's CURRENT "
        "source_files:\n\n"
        f"{changes_text}\n\n"
        "Rules:\n"
        "- Base each file on the types in that phase's source files; do not "
        "invent new types.\n"
        "- Do NOT modify any other files. Only edit engine_overview.txt and "
        "phase_NN_types.txt files directly under "
        "fm_agent/spec_prompts/domain_context/. Do NOT edit files under "
        "fm_agent/spec_prompts/domain_context/user_knowledge/.\n"
        f"{overview_rule}"
    )

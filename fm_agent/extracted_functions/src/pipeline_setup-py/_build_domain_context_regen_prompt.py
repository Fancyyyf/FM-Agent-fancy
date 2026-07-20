# [SPEC]
# Unit: src/pipeline_setup.py
#
# _build_domain_context_regen_prompt(phase_source_files, phase_cleanup=None) -> str
#
# Pre-condition:
#   - phase_source_files is a dict mapping integer phase numbers to non-empty lists of source file path strings
#   - phase_cleanup, when provided, is a dict that may contain key "removed_phases" (a list of values, each either an integer phase number or None) and key "renumbered" (a dict mapping old phase numbers to new phase numbers, where either the old or new value may be None)
#
# Post-condition:
#   - Returns a prompt string intended for consumption by an LLM agent
#   - The prompt instructs the agent to regenerate, from scratch, the file phase_NN_types.txt under fm_agent/spec_prompts/domain_context/ for every integer phase number present in phase_source_files, deriving its content from the real types, structs, and invariants defined in the source files associated with that phase
#   - For every phase in the prompt's regeneration list, the list of its source file paths is included; the list appears in sorted phase-number order
#   - When phase_cleanup specifies removal of one or more non-None phase numbers (via the "removed_phases" key), the prompt instructs the agent to update engine_overview.txt so its phase-numbered references match the final phases.json after those removals
#   - When phase_cleanup specifies renumbering of one or more phases (via non-None entries in the "renumbered" dict where the old and new phase numbers differ), the prompt instructs the agent to update engine_overview.txt so its phase-numbered references match the final phases.json after those renumberings
#   - When neither removal nor renumbering applies, the prompt instructs the agent to leave engine_overview.txt unchanged unless it explicitly names a phase number that changed
#   - The prompt constrains the agent to modify only files under fm_agent/spec_prompts/domain_context/ and prohibits modification of files under its user_knowledge/ subdirectory
# [SPEC]

# [INFO]
# (no callees)
# [INFO]

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

def _build_module_description_prompt(modified_modules, phases_json):
    """Compose the instruction telling the agent to refresh the descriptions of
    modules whose source-file list changed during post-processing.

    ``modified_modules`` is the list produced by ``_collect_changed_modules``; each
    entry names a module by its CURRENT phase number and module name. Modules that
    own no source files in ``phases_json`` are skipped — there is nothing to
    describe, so they are left out of the prompt.
    """
    try:
        with open(phases_json, "r") as f:
            data = json.load(f)
    except (OSError, ValueError):
        data = {"phases": []}
    source_files_by_key = {}
    for phase in data.get("phases", []):
        for module in phase.get("modules", []):
            source_files_by_key[(phase.get("phase"), module.get("name", ""))] = list(
                module.get("source_files", [])
            )

    lines = []
    for m in modified_modules:
        if not source_files_by_key.get((m["phase"], m["module"])):
            # Module owns no files; nothing to describe, so leave it out.
            continue
        lines.append(f"  - phase {m['phase']} module \"{m['module']}\"")
    if not lines:
        return None
    changes_text = "\n".join(lines)

    return (
        "Here is a list of modules in fm_agent/phases.json:\n\n"
        f"{changes_text}\n\n"
        "Please update the \"description\" field of each module above so that it accurately "
        "describes the source files it now owns.\n"
        "Rules:\n"
        "- Edit ONLY the \"description\" field of the listed modules in "
        "fm_agent/phases.json.\n"
        "- Do NOT change any \"source_files\", \"phase\", \"name\", "
        "\"depends_on_phases\", or the phase structure in any way.\n"
        "- Do NOT touch modules that are not in the list above.\n"
        "- Keep the JSON valid.\n"
        "- Do NOT modify any project source file; only edit fm_agent/phases.json."
    )

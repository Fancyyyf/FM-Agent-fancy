# [SPEC]
# Unit: src/pipeline_setup.py
#
# _build_module_description_prompt(modified_modules, phases_json) -> Optional[str]
#
# Pre-condition:
#   - modified_modules is an iterable of dicts, each containing at minimum
#     "phase" (int) and "module" (str) keys.
#   - phases_json is a string path to a JSON file. If the file exists, its
#     content conforms to the phases.json schema: a JSON object with a
#     "phases" array where each phase has "phase" (int) and "modules"
#     (array of objects with "name" (str) and "source_files" (array of str)).
#
# Post-condition:
#   - If phases_json cannot be opened or its content is not valid JSON,
#     behaves as if phases were an empty list.
#   - Returns None when none of the modules named in modified_modules
#     has a non-empty source_files array in phases_json.
#   - Otherwise, returns a string containing an agent prompt. The prompt
#     enumerates every module in modified_modules that still owns at least
#     one source file according to phases_json, each formatted as a
#     bulleted line identifying the module by its current phase number
#     and module name. The prompt includes explicit constraints that the
#     agent must: edit only the "description" field of the listed modules
#     in fm_agent/phases.json; not modify "source_files", "phase", "name",
#     "depends_on_phases", or the phase structure; not touch any unlisted
#     module; keep the JSON valid; and not modify any project source file.
#   - This function has no side effects: it does not write to any file.
# [SPEC]

# [INFO]
# (no callees)
# [INFO]

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

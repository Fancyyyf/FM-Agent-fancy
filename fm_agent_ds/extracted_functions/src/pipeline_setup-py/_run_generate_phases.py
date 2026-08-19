def _run_generate_phases(proj_dir, work_dir, script_dir, is_incremental=False,
                         resume=False, submodules=None, plugin_stage=None,
                         plugin_root=None):
    """Stage 1: generate phase.json — input target code, output phases.json."""
    if plugin_stage is not None:
        if plugin_stage.type == "pass":
            print("[Pipeline] Stage 1/6: Plugin stage 'generate_phase_plan' type=pass, skipping.")
            return
        if plugin_stage.type == "replace":
            print("[Pipeline] Stage 1/6: Plugin stage 'generate_phase_plan' type=replace, running plugin command.")
            from .plugin import run_plugin_command
            run_plugin_command(plugin_stage.replace_cmd, plugin_root, proj_dir, label="generate_phase_plan")
            return

    phases_json = os.path.join(work_dir, "phases.json")
    prev_mtime = os.path.getmtime(phases_json) if os.path.exists(phases_json) else None

    phase_plan_errors = (
        _phase_plan_schema_errors(phases_json)
        if os.path.exists(phases_json)
        else []
    )
    _resume_skip = resume and _phase_plan_complete(work_dir)
    if _resume_skip:
        print("[Pipeline] Stage 1/6: RESUME — phases.json found, skipping phase plan generation.")

    if plugin_stage is not None and plugin_stage.type == "modify" and plugin_stage.input_md:
        workflow_src = str(plugin_root / plugin_stage.input_md)
        workflow_dst = os.path.join(work_dir, "workflow_generate_phases.md")
        shutil.copy2(workflow_src, workflow_dst)
        user_knowledge_paths = list_staged_domain_knowledge_relpaths(work_dir)
        if user_knowledge_paths:
            with open(workflow_dst, "a") as _f:
                _f.write(
                    "\n---\n\n"
                    "## User-Provided Domain Knowledge\n\n"
                    "The user supplied extra Markdown files with domain knowledge for this run. "
                    "Read these files before writing `phases.json` and the generated domain "
                    "context files. Use them only as contextual knowledge about intended "
                    "behavior, terminology, business rules, data encodings, and invariants; "
                    "do NOT include these Markdown files as project source files in "
                    "`phases.json`, and do NOT edit or summarize them in place.\n\n"
                    f"{format_domain_knowledge_bullets(user_knowledge_paths)}\n"
                )
    else:
        _prepare_workflow_file(proj_dir, work_dir, script_dir, "workflow_generate_phases.md")

    fm_reminder = ("IMPORTANT: The fm_agent/ directory is NOT part of the project source code. "
                    "It is a workspace for storing your output files only. "
                    "Do NOT include fm_agent/ paths in phases.json. "
                    "Do NOT modify any existing project files.")
    incremental_reminder = ("IMPORTANT: An existing fm_agent/phases.json from a previous run is already "
                            "present. Do NOT regenerate it from scratch. Instead, inspect the current "
                            "state of the source code and UPDATE the existing fm_agent/phases.json so it "
                            "reflects the current version of the code: add modules and source files that "
                            "are new, remove entries whose files no longer exist, and adjust phases as "
                            "needed. Preserve entries that are still accurate.")
    submodule_reminder = ""
    if submodules:
        allowed = ", ".join(f"`{submodule}/`" for submodule in submodules)
        submodule_reminder = (
            "IMPORTANT: Only process source files under these project-relative "
            f"subdirectories: {allowed}. Do NOT include files outside these "
            "subdirectories in phases.json."
        )

    for attempt in range(1, OPENCODE_MAX_RETRIES + 1):
        if _resume_skip:
            break
        if attempt == 1 and not resume:
            prompt = f"Follow the instructions in the attached file. {fm_reminder} {submodule_reminder}"
        else:
            prompt = ("A previous attempt was interrupted and may have already produced some of the "
                      "required output files. Follow the instructions in the attached file, but FIRST "
                      "check the current progress in fm_agent/ (e.g. phases.json). Keep any existing valid "
                      "output as-is and only generate the files that are missing or incomplete — do NOT "
                      f"regenerate or overwrite work that is already done. {fm_reminder} {submodule_reminder}")
        if is_incremental:
            prompt = f"{prompt} {incremental_reminder}"
        if phase_plan_errors:
            formatted_errors = "\n".join(
                f"- {error}" for error in phase_plan_errors
            )
            schema_repair_prompt = (
                "IMPORTANT: The existing fm_agent/phases.json is valid JSON or "
                "partially generated, but it does not match the required schema. "
                "Read the project source files and repair these problems:\n"
                f"{formatted_errors}\n"
                "Do not use an empty source_files array merely to satisfy the schema. "
                "Use an empty array only when the module genuinely owns no source files."
            )
            prompt = f"{prompt}\n\n{schema_repair_prompt}"
        prompt_file = os.path.join(proj_dir, "fm_agent", "workflow_generate_phases.md")
        command = build_llm_cli_command(
            model=OPENCODE_SETUP_MODEL,
            prompt=prompt,
            cwd=proj_dir,
            files=[prompt_file],
        )
        try:
            run_opencode_traced(
                proj_dir=proj_dir,
                work_dir=work_dir,
                command=command,
                stage="generate_phases_json",
                input_files=[
                    "fm_agent/workflow_generate_phases.md",
                    *list_staged_domain_knowledge_relpaths(work_dir),
                ],
                output_files=[
                    "fm_agent/phases.json",
                ],
                summary=f"OpenCode generate phases.json attempt {attempt}",
                metadata={"attempt": attempt},
            )
        except subprocess.CalledProcessError as e:
            logging.warning(f"Stage 1 attempt {attempt}: opencode exited with code {e.returncode}")

        phase_plan_errors = (
            _phase_plan_schema_errors(phases_json)
            if os.path.exists(phases_json)
            else ["phases.json is missing"]
        )

        phase_plan_ready = False
        if not phase_plan_errors:
            if submodules:
                phase_plan_ready = _phases_cover_current_sources(
                    phases_json, proj_dir, submodules
                )
            elif is_incremental:
                phase_plan_ready = (
                    os.path.getmtime(phases_json) != prev_mtime
                    or _phases_cover_current_sources(phases_json, proj_dir)
                )
            else:
                phase_plan_ready = True
        if phase_plan_ready:
            break

        failure = "update phases.json" if is_incremental else "produce phases.json"
        if phase_plan_errors:
            missing = (
                "phases.json schema validation failed: "
                + "; ".join(phase_plan_errors)
            )
        else:
            missing = (
                "phases.json was not updated"
                if is_incremental
                else "phases.json missing or invalid"
            )
        if attempt < OPENCODE_MAX_RETRIES:
            delay = 10
            print(
                f"[Pipeline] Stage 1 failed to {failure} (attempt {attempt}/{OPENCODE_MAX_RETRIES}). "
                f"Retrying in {delay}s..."
            )
            logging.warning(f"Stage 1 attempt {attempt} failed: {missing}. Retrying in {delay}s.")
            time.sleep(delay)
        else:
            print(
                f"[Pipeline] ERROR: Stage 1 failed after {OPENCODE_MAX_RETRIES} attempts. "
                f"{missing}. "
                f"Check {os.path.basename(proj_dir)}/fm_agent/trace/ for details."
            )
            sys.exit(1)

    if plugin_stage is not None and plugin_stage.type == "modify" and plugin_stage.output_process:
        print("[Pipeline] Stage 1/6: Running plugin post-process for generate_phase_plan...")
        from .plugin import run_plugin_command
        run_plugin_command(plugin_stage.output_process, plugin_root, proj_dir, label="generate_phase_plan post-process")

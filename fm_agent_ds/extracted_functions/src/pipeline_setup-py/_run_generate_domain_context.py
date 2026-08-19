def _run_generate_domain_context(proj_dir, work_dir, script_dir, resume=False,
                                 plugin_stage=None, plugin_root=None):
    """Stage 2: generate domain context — input phases.json, output domain context
    files for each phase.
    """
    if plugin_stage is not None:
        if plugin_stage.type == "pass":
            print("[Pipeline] Stage 2/6: Plugin stage 'generate_domain_context' type=pass, skipping.")
            return
        if plugin_stage.type == "replace":
            print("[Pipeline] Stage 2/6: Plugin stage 'generate_domain_context' type=replace, running plugin command.")
            from .plugin import run_plugin_command
            run_plugin_command(plugin_stage.replace_cmd, plugin_root, proj_dir, label="generate_domain_context")
            return

    _resume_skip = resume and _domain_context_complete(work_dir)
    if _resume_skip:
        print("[Pipeline] Stage 2/6: RESUME — domain context files found, skipping domain context generation.")

    if plugin_stage is not None and plugin_stage.type == "modify" and plugin_stage.input_md:
        workflow_src = str(plugin_root / plugin_stage.input_md)
        workflow_dst = os.path.join(work_dir, "workflow_generate_domain_context.md")
        shutil.copy2(workflow_src, workflow_dst)
        user_knowledge_paths = list_staged_domain_knowledge_relpaths(work_dir)
        if user_knowledge_paths:
            with open(workflow_dst, "a") as _f:
                _f.write(
                    "\n---\n\n"
                    "## User-Provided Domain Knowledge\n\n"
                    "The user supplied extra Markdown files with domain knowledge for this run. "
                    "Read these files before writing the domain context files. "
                    "Use them only as contextual knowledge about intended "
                    "behavior, terminology, business rules, data encodings, and invariants.\n\n"
                    f"{format_domain_knowledge_bullets(user_knowledge_paths)}\n"
                )
    else:
        _prepare_workflow_file(proj_dir, work_dir, script_dir, "workflow_generate_domain_context.md")

    fm_reminder = ("IMPORTANT: The fm_agent/ directory is NOT part of the project source code. "
                    "It is a workspace for storing your output files only. "
                    "Do NOT modify any existing project files.")

    for attempt in range(1, OPENCODE_MAX_RETRIES + 1):
        if _resume_skip:
            break
        if attempt == 1 and not resume:
            prompt = (
                "Read fm_agent/phases.json first. "
                "Then follow the instructions in the attached file. "
                + fm_reminder
            )
        else:
            prompt = ("A previous domain-context generation attempt was interrupted and may have already "
                      "produced some of the required output files. Read fm_agent/phases.json first. "
                      "Then follow the instructions in the attached file, but FIRST "
                      "check the current progress in fm_agent/spec_prompts/domain_context/. "
                      "Keep any existing valid output as-is and only generate the files that are missing or "
                      f"incomplete — do NOT regenerate or overwrite work that is already done. {fm_reminder}")
        prompt_file = os.path.join(proj_dir, "fm_agent", "workflow_generate_domain_context.md")
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
                stage="generate_domain_context",
                input_files=[
                    "fm_agent/workflow_generate_domain_context.md",
                    "fm_agent/phases.json",
                    *list_staged_domain_knowledge_relpaths(work_dir),
                ],
                output_files=[
                    "fm_agent/spec_prompts/domain_context/engine_overview.txt",
                ],
                summary=f"OpenCode generate domain context attempt {attempt}",
                metadata={"attempt": attempt},
            )
        except subprocess.CalledProcessError as e:
            logging.warning(f"Stage 2 attempt {attempt}: opencode exited with code {e.returncode}")

        if _domain_context_complete(work_dir):
            break

        if attempt < OPENCODE_MAX_RETRIES:
            delay = 10
            print(
                f"[Pipeline] Stage 2 failed to produce domain context "
                f"(attempt {attempt}/{OPENCODE_MAX_RETRIES}). "
                f"Retrying in {delay}s..."
            )
            logging.warning(f"Stage 2 attempt {attempt} failed: domain context outputs missing. Retrying in {delay}s.")
            time.sleep(delay)
        else:
            print(
                f"[Pipeline] ERROR: Stage 2 failed after {OPENCODE_MAX_RETRIES} attempts. "
                f"Domain context outputs missing. "
                f"Check {os.path.basename(proj_dir)}/fm_agent/trace/ for details."
            )
            sys.exit(1)

    if plugin_stage is not None and plugin_stage.type == "modify" and plugin_stage.output_process:
        print("[Pipeline] Stage 2/6: Running plugin post-process for generate_domain_context...")
        from .plugin import run_plugin_command
        run_plugin_command(plugin_stage.output_process, plugin_root, proj_dir, label="generate_domain_context post-process")

def _run_spec_generation_batch(
    proj_dir,
    work_dir,
    attempt,
    phase_num,
    layer_idx,
    batch_rel_dir,
    batch_info,
):
    # Run one batch end-to-end so the executor can refill slots as soon as a
    # batch finishes, instead of waiting for a whole chunk barrier.
    batch_file = batch_info["file"]
    batch_prompt_rel = os.path.join(batch_rel_dir, batch_file)
    function_files = batch_info.get("functions", [])
    function_ids = [
        function_id_from_extracted_path(func_rel)
        for func_rel in function_files
    ]
    fm_reminder = ("IMPORTANT: fm_agent/ is your output workspace, not project source. "
                    "Do NOT modify any existing project files.")
    if attempt == 1:
        prompt = (
            f"Process the batch prompt file at {batch_prompt_rel}. "
            f"Read it and fm_agent/spec_prompts/system_prompt.md, "
            f"generate behavioral specs for each function listed, "
            f"and write the .spec.json and .info.json files for each function. "
            f"Do not modify the function source files. {fm_reminder}"
        )
    else:
        prompt = (
            f"Continue processing the batch prompt file at {batch_prompt_rel}. "
            f"Some functions may already have valid specs from a previous attempt. "
            f"Check each function listed in the batch prompt. Skip it only when both "
            f"its .spec.json and .info.json files contain valid JSON matching the "
            f"schemas in fm_agent/spec_prompts/system_prompt.md. If either sidecar "
            f"is missing, malformed, or schema-invalid, rewrite the complete "
            f".spec.json and .info.json files for that function. "
            f"Do not modify the function source files. {fm_reminder}"
        )
    prompt_file = os.path.join(proj_dir, "fm_agent", "workflow_spec_step4_batch.md")
    command = build_llm_cli_command(
        model=OPENCODE_SPEC_MODEL,
        prompt=prompt,
        cwd=proj_dir,
        files=[prompt_file],
    )
    try:
        result = run_opencode_traced(
            proj_dir=proj_dir,
            work_dir=work_dir,
            command=command,
            stage="spec_generation",
            function_ids=function_ids,
            input_files=[
                "fm_agent/workflow_spec_step4_batch.md",
                batch_prompt_rel,
                "fm_agent/spec_prompts/system_prompt.md",
                *list_staged_domain_knowledge_relpaths(work_dir),
            ],
            output_files=[
                f"{function_file}.spec.json"
                for function_file in function_files
            ] + [
                f"{function_file}.info.json"
                for function_file in function_files
            ],
            summary=f"OpenCode spec generation for {batch_file}",
            metadata={
                "attempt": attempt,
                "phase": phase_num,
                "layer": layer_idx,
                "batch_file": batch_file,
            },
        )
        return result.returncode
    except subprocess.CalledProcessError as exc:
        return exc.returncode

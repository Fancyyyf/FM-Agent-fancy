def reasoner(func, spec, info, language, trace_context=None):
    trace_context = trace_context or {}
    trace_dir = trace_context.get("trace_dir")
    # Step 1: Parse pre-condition and post-condition directly from spec
    pre_condition, spec_post_condition = _parse_spec_conditions(spec)
    if not pre_condition or not spec_post_condition:
        return "Failed to parse pre/post conditions from the spec."

    # Step 2: Split function into code blocks (each >= GRANULARITY lines)
    blocks = _split_into_blocks_braced(func, language)

    # Step 3: Process each block sequentially
    current_pre = pre_condition
    for i, block in enumerate(blocks):
        # Generate post-condition using Claude Sonnet 4.6
        trace_meta = {
            "function_id": trace_context.get("function_id"),
            "function_file": trace_context.get("function_file"),
            "language": language,
            "block_index": i,
            "block_count": len(blocks),
        }
        post_condition = _generate_block_post_condition(
            block,
            current_pre,
            info,
            language,
            trace_dir=trace_dir,
            trace_meta=trace_meta,
        )
        if not post_condition:
            return f"Failed to generate post-condition for block {i+1}."

        # Check against spec post-condition if block has terminating statements
        # or if this is the last block (implicit return at end of function)
        is_last_block = (i == len(blocks) - 1)
        if _has_terminating_statement(block, language) or is_last_block:
            passed, stmts, post_cond, reason = _check_post_implies_spec(
                block,
                post_condition,
                spec_post_condition,
                info,
                language,
                trace_dir=trace_dir,
                trace_meta=trace_meta,
            )
            if not passed:
                return (
                    f"Verification FAILED.\n"
                    f"Statements triggering the violation:\n{stmts}\n\n"
                    f"Post-condition:\n{post_cond}\n\n"
                    f"Reason for violation:\n{reason}"
                )

        # Use current block's post-condition as next block's pre-condition
        current_pre = post_condition

    return "The function passes the verification. All code blocks satisfy the specification's post-condition."

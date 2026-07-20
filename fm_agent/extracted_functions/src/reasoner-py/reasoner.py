# [SPEC]
# Unit: src/reasoner-py/reasoner.py
#
# reasoner(func, spec, info, language, trace_context=None) -> str
#
# Pre-condition:
#   - func is a non-empty string containing the body of a function written in the language identified by `language`
#   - spec is a string containing a behavioral specification with distinct pre-condition and post-condition sections
#   - info is a mapping from callee function names to their behavioral specifications (what each callee requires and guarantees)
#   - language is a string identifying the source programming language (e.g., "python", "rust", "c", "cpp", "java", "go")
#   - trace_context, when not None, is a dict that may contain the keys "trace_dir", "function_id", and "function_file" used for recording verification traces
#
# Post-condition:
#   - Returns a string whose first line begins with "The function passes the verification." or "Verification FAILED."
#   - Returns a string whose first line begins with "Failed to parse" when the `spec` argument does not contain extractable pre-condition and post-condition sections
#   - Returns a string identifying a specific failure location (by block number) when any required computation step yields no result
#   - On a mismatch verdict, the returned string provides: the code statements that violate the specification, the post-condition computed immediately before the violation, and the reason the computed post-condition does not imply the specification's required post-condition
#   - On a pass verdict, the returned string states that all code blocks satisfy the specification's post-condition
#   - The specification's pre-condition is the assumed state at function entry. If analysis of the function body shows that the specification's post-condition is guaranteed to hold given that assumption, the verdict is pass. If the body can reach a state that violates the specification's post-condition, the verdict is fail with evidence showing where and why the violation occurs.
# [SPEC]

# [INFO]
# _parse_spec_conditions(spec)
#   Pre-condition: spec is a string containing specification text
#   Post-condition: Returns a tuple (pre_condition, post_condition) where each element is either a string describing the condition, or an empty/falsy value indicating the corresponding condition could not be extracted
# [SPLIT]
# _split_into_blocks_braced(func, language)
#   Pre-condition: func is a string containing function body text, language identifies the source programming language
#   Post-condition: Returns a list of strings, each being a syntactically complete and non-overlapping segment of the function. For brace-delimited languages, segment boundaries occur only at brace depths matching the entry depth. The ordered concatenation of all returned segments reconstructs the original function body.
# [SPLIT]
# _generate_block_post_condition(block, pre_condition, info, language, trace_dir=None, trace_meta=None)
#   Pre-condition: block is a string containing code statements, pre_condition is a string describing the state assumed before the block, info is a callee specification mapping, language identifies the source language
#   Post-condition: Returns either a string describing the strongest post-condition that must hold after executing the block from the given pre-condition, or None if the post-condition could not be determined
# [SPLIT]
# _has_terminating_statement(block, language)
#   Pre-condition: block is a string containing code statements, language identifies the source language
#   Post-condition: Returns True when every syntactically reachable path through the block ends in an unconditional termination (return, raise, system exit, or language-specific equivalent). Returns False when there exists at least one reachable path through the block that can fall through to subsequent code without terminating.
# [SPLIT]
# _check_post_implies_spec(block, post_condition, spec_post_condition, info, language, trace_dir=None, trace_meta=None)
#   Pre-condition: post_condition is a string describing the computed post-condition, spec_post_condition is a string describing the specification's required post-condition, info is a callee specification mapping, language identifies the source language
#   Post-condition: Returns a tuple (passed, stmts, post_cond, reason). When the computed post-condition logically implies the specification's post-condition, returns (True, None, None, None). When it does not, returns (False, offending_statements, computed_post_condition, reason_for_violation).
# [INFO]

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

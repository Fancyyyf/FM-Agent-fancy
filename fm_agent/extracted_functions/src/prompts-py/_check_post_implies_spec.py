def _check_post_implies_spec(block, post_condition, spec_post_condition, knowledge, language,
                             trace_dir=None, trace_meta=None):
    info_str = f"\nAdditional context:\n{knowledge}" if knowledge else ""
    lang_expertise = _LANGUAGE_EXPERTISE.get(language.lower(), f"You are an expert in logic, formal verification, and {language} programming. ")
    messages = [
        {"role": "system", "content": (
            lang_expertise +
            "Given a code block, its post-condition A (what the code actually does), and a specification post-condition B (what the code should do), "
            "determine whether there exists a concrete valid input where the code's behavior (A) violates the specification (B). "
            "Focus on finding CONCRETE COUNTEREXAMPLES: specific input values where the code produces an output that does not satisfy the specification. "
            "Check these common violation patterns:\n"
            "  1. The code rejects/filters out inputs that the specification says should be accepted (missing cases). "
            "Enumerate all required cases from the specification and the relevant language standard, and check each one against what the code handles.\n"
            "  2. The code accepts inputs that the specification says should be rejected.\n"
            "  3. The code produces a wrong output value for a valid input.\n"
            "For each potential violation, construct a specific input, trace what the code does (A), and check if the specification (B) is satisfied.\n"
            "Return only a valid JSON object. Do not include markdown, tags, or prose. "
            "Use exactly this schema: "
            "{\"verdict\": \"MATCH|MISMATCH\", \"counterexample\": string|null, "
            "\"offending_statements\": string|null, \"reason\": string}. "
            "For MISMATCH, counterexample, offending_statements, and reason must be non-empty strings; "
            "offending_statements must preserve any 'Line N:' prefixes from the code block. "
            "For MATCH, counterexample and offending_statements must be null or empty, and reason may be empty."
        )},
        {"role": "user", "content": (
            f"Programming language: {language}\n\n"
            f"Code block:\n```{language.lower()}\n{block}\n```\n\n"
            f"Condition A (what the code actually does):\n{post_condition}\n\n"
            f"Condition B (what the specification requires):\n{spec_post_condition}\n"
            f"{info_str}\n"
            "Is there a concrete valid input where the code's behavior violates the specification? "
            "Enumerate all cases required by condition B and check if condition A covers each one. "
            "Provide a specific counterexample if any case is missing. Return only the JSON object."
        )}
    ]
    trace_meta = trace_meta or {}
    for attempt in range(1, MAX_SPC_ITER + 1):
        event_id = new_event_id("llm")
        started = utc_now_iso()
        response = None
        usage = {}
        try:
            response, usage = _retry_create(_llm_provider_client, REASONER_SPEC_CHECK_MODEL, messages)
        except Exception as exc:
            event = {
                "event_id": event_id,
                "type": "llm_call",
                "stage": "verification",
                "status": "error",
                "start_time": started,
                "end_time": utc_now_iso(),
                "summary": f"LLM implication check failed: {exc}",
                "metadata": {
                    **trace_meta,
                    "purpose": "check_post_implies_spec",
                    "model": REASONER_SPEC_CHECK_MODEL,
                    "attempt": attempt,
                    "error": str(exc),
                },
            }
            record_llm_exchange(trace_dir, event_id, event, messages)
            raise
        parsed_result = None
        parse_error = None
        try:
            has_violation, stmts, reason, parsed_result = _parse_spec_check_json(response)
            status = "mismatch" if has_violation else "success"
        except ValueError as exc:
            has_violation = None
            stmts = reason = None
            parse_error = str(exc)
            status = "format_error"
        event = {
            "event_id": event_id,
            "type": "llm_call",
            "stage": "verification",
            "status": status,
            "start_time": started,
            "end_time": utc_now_iso(),
            "summary": "Checked whether actual post-condition implies the spec",
            "metadata": {
                **trace_meta,
                "purpose": "check_post_implies_spec",
                "model": REASONER_SPEC_CHECK_MODEL,
                "attempt": attempt,
                "usage": usage,
                "parsed_json": parsed_result,
                "parse_error": parse_error,
            },
        }
        record_llm_exchange(trace_dir, event_id, event, messages, response)
        if has_violation is not None:
            if has_violation:
                stmts = stmts or "(unable to extract)"
                reason = reason or "(unable to extract)"
                return False, stmts, post_condition, reason
            else:
                return True, None, None, None
        messages = messages + [
            {"role": "assistant", "content": response or ""},
            {
                "role": "user",
                "content": (
                    "Return only valid JSON with schema: "
                    "{\"verdict\": \"MATCH|MISMATCH\", "
                    "\"counterexample\": string|null, "
                    "\"offending_statements\": string|null, "
                    "\"reason\": string}. "
                    "For MISMATCH, all evidence fields must be non-empty strings. "
                    "For MATCH, counterexample and offending_statements must be null or empty, and reason may be empty."
                ),
            }
        ]
    raise ValueError("Could not parse a valid structured JSON verdict from spec-check response.")

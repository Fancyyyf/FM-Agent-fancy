# [SPEC]
# Unit: src/verification.py
#
# _verify_single_file(file_path, input_dir, output_dir, language, work_dir=None, resume=False) -> (str, str)
#
# Pre-condition:
#   - file_path is the absolute path to an extracted-function file under
#     input_dir (which is fm_agent/extracted_functions/ or equivalent)
#   - input_dir and output_dir are existing directories; output_dir is
#     writable (typically fm_agent/logic_verification_results/)
#   - language is a non-empty string identifying the source language of the
#     function (one of the keys in EXT_TO_LANG, e.g. "Python", "Rust")
#   - work_dir is either None or an existing directory containing a
#     fm_agent/ workspace tree
#   - resume is a boolean
#
# Post-condition:
#   - Returns a tuple (file_path, verdict) where verdict is one of
#     "SKIPPED", "MATCH", "MISMATCH", or "ERROR"
#   - When resume is True and a valid (JSON-parsable) result JSON already
#     exists at output_dir/<relative-path>.json, returns the stored verdict
#     without re-running the reasoner; a corrupted result file triggers a
#     fresh verification
#   - Reads the [SPEC] block from file_path; when no spec exists in the
#     file, returns ("SKIPPED") and writes nothing to output_dir
#   - Otherwise, invokes a reasoner with the function body, the spec, any
#     domain knowledge (from the spec file and/or from staged knowledge
#     files under work_dir), and the declared language
#   - Produces a result JSON at output_dir/<relative-path>.json containing
#     at minimum {"function": file_path, "verdict": verdict} plus, when the
#     verdict is "MISMATCH", a "gaps" object with four populated fields:
#     spec_claim, actual_behavior, code_evidence, and trigger_condition
#   - Determines the verdict from the reasoner's response:
#       * Contains the exact phrase "passes the verification" → "MATCH"
#       * Starts with the exact prefix "Failed to " → "ERROR" with the full
#         response stored as the error reason
#       * Otherwise → "MISMATCH", with gaps extracted by matching the
#         reasoner's structured output sections (statements triggering the
#         violation, post-condition, and reason for violation)
#   - On any unhandled exception during parsing, reasoning, or result
#     writing: verdict is "ERROR" with the exception message stored in the
#     result JSON
#   - String values in the output dict are sanitized before serialization
#     (the sanitization preserves JSON-roundtrip fidelity)
#   - Writes exactly one result JSON per invocation (either skipped or
#     produced), and the output file is a valid JSON object
# [SPEC]

# [INFO]
# parse_input_function(file_path) -> (str, str, str) | (None, None, None)
#   Pre-condition: file_path is the path to an extracted-function file that
#     may contain [SPEC] and [INFO] comment blocks prepended to source code
#   Post-condition: returns (function_body, spec_text, knowledge_text);
#     function_body is the source code after any prepended spec blocks;
#     spec_text is the content between [SPEC] markers, or None if absent;
#     knowledge_text is the content between [INFO] markers, or None if
#     absent
# [SPLIT]
# _parse_spec_conditions(spec) -> (str, str)
#   Pre-condition: spec is a non-empty string containing a [SPEC] block
#     with "Pre-condition:" and "Post-condition:" sections
#   Post-condition: returns (pre_condition_text, post_condition_text) where
#     each is the text of the respective section extracted from the spec
# [SPLIT]
# load_staged_domain_knowledge_text(work_dir) -> str
#   Pre-condition: work_dir is a valid directory path whose fm_agent/
#     subtree may contain staged domain-knowledge Markdown files
#   Post-condition: returns the concatenated text content of all staged
#     domain-knowledge Markdown files under work_dir, with a single newline
#     separating each file's content; returns an empty string when no
#     staged knowledge files exist
# [SPLIT]
# reasoner(func, spec, knowledge, language, trace_context) -> str
#   Pre-condition: func is the function source code as a string,
#     spec is the [SPEC] block text, knowledge is a string of domain
#     knowledge (may be empty), language identifies the source language,
#     trace_context is a dict with trace_dir, function_id, and
#     function_file keys or None
#   Post-condition: returns a string containing the reasoner's verdict:
#     either "passes the verification", a result starting with
#     "Failed to " indicating an error, or a structured mismatch report
#     with sections for statements, post-condition, and reason
# [SPLIT]
# _sanitize_strings(obj) -> dict
#   Pre-condition: obj is a dict whose values may contain non-printable
#     characters or other content that would break JSON serialization
#   Post-condition: returns a dict with the same keys as obj; every string
#     value in the returned dict is sanitized so that json.dump produces
#     a valid JSON output
# [INFO]

def _verify_single_file(file_path, input_dir, output_dir, language, work_dir=None, resume=False):
    """Verify a single file and write the result JSON."""
    # Skip if resuming and a valid result already exists
    rel = os.path.relpath(file_path, input_dir)
    output_path = os.path.join(output_dir, os.path.splitext(rel)[0] + ".json")
    if resume and os.path.exists(output_path):
        try:
            with open(output_path) as f:
                existing = json.load(f)
            verdict = existing.get("verdict", "ERROR")
            logging.info(f"Already verified, skipping: {file_path} (verdict={verdict})")
            return file_path, verdict
        except (json.JSONDecodeError, OSError):
            pass  # re-verify if existing result is corrupted

    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    try:
        func, spec, knowledge = parse_input_function(file_path)
        if not spec:
            return file_path, "SKIPPED"

        _, spec_post = _parse_spec_conditions(spec)
        trace_context = None
        if work_dir:
            rel_function = os.path.relpath(file_path, input_dir)
            trace_context = {
                "trace_dir": os.path.join(work_dir, "trace"),
                "function_id": os.path.splitext(rel_function)[0].replace(os.sep, "::"),
                "function_file": os.path.join("extracted_functions", rel_function).replace(os.sep, "/"),
            }
        domain_knowledge = load_staged_domain_knowledge_text(work_dir) if work_dir else ""
        if domain_knowledge:
            knowledge = f"{knowledge}\n\n{domain_knowledge}" if knowledge else domain_knowledge
        result = reasoner(func, spec, knowledge, language, trace_context=trace_context)

        if "passes the verification" in result:
            output = {"function": file_path, "verdict": "MATCH", "gaps": None}
        elif result.startswith("Failed to "):
            output = {"function": file_path, "verdict": "ERROR", "gaps": None, "error": result}
        else:
            stmts = post_cond = reason_text = ""
            stmts_match = re.search(
                r"Statements triggering the violation:\n(.*?)\n\nPost-condition:", result, re.DOTALL
            )
            post_match = re.search(
                r"Post-condition:\n(.*?)\n\nReason for violation:", result, re.DOTALL
            )
            reason_match = re.search(r"Reason for violation:\n(.*)", result, re.DOTALL)

            if stmts_match:
                stmts = stmts_match.group(1).strip()
            if post_match:
                post_cond = post_match.group(1).strip()
            if reason_match:
                reason_text = reason_match.group(1).strip()

            output = {
                "function": file_path,
                "verdict": "MISMATCH",
                "gaps": {
                    "spec_claim": spec_post or "",
                    "actual_behavior": post_cond,
                    "code_evidence": stmts,
                    "trigger_condition": reason_text,
                },
            }
    except Exception as exc:
        logging.exception(f"Verification failed for {file_path}")
        output = {"function": file_path, "verdict": "ERROR", "gaps": None, "error": str(exc)}

    output = _sanitize_strings(output)
    with open(output_path, "w") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    return file_path, output["verdict"]

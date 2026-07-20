# [SPEC]
# Unit: fm_agent/extracted_functions/src/scope-py/_llm_rerank.py
#
# _llm_rerank(funcs_info: list[dict], source_lines: list[str], filepath: str,
#             issue: str, top_k: int, llm_client: Any, model: str) -> list[str] | None
#
# Pre-condition:
#   - funcs_info is a non-empty list of dicts, each with a unique 'name' (str)
#     key, plus 'start' and 'end' keys (int, 1‑based line numbers) identifying
#     the function's source span within source_lines.
#   - source_lines is a list[str] representing the full source text, with at
#     least max(func['end'] for func in funcs_info) elements.
#   - filepath is a non-empty string identifying the source file.
#   - issue is a string describing developer intent.
#   - top_k is a positive integer.
#   - llm_client is a live LLM client supporting chat completions.
#   - model is a non-empty string identifying the LLM model to query.
#
# Post-condition:
#   - If the LLM produces a valid response, returns a list of function names
#     (non‑empty strings), each drawn exclusively from the set of names in
#     funcs_info, in descending order of relevance to the issue as judged by
#     the LLM, with no duplicate names and length at most top_k.
#   - If the LLM does not produce a valid response after the allowed number of
#     attempts, returns None.
#   - The function is idempotent with respect to funcs_info, source_lines,
#     filepath, and issue: repeated calls with the same arguments may produce
#     different rankings (LLM non‑determinism) but each valid ranking obeys
#     the same contract.
# [SPEC]

# [INFO]
# _build_func_list_text(funcs_info: list[dict], source_lines: list[str]) -> str
#   Pre-condition: funcs_info entries have 'name', 'start', and 'end' keys; source_lines is a list of source text lines covering all spans in funcs_info.
#   Post-condition: Returns a string containing, for each function in funcs_info, its name and the exact source text extracted from source_lines delimiting its start and end lines.
# [SPLIT]
# _parse_json_response(text: str) -> list
#   Pre-condition: text is a string.
#   Post-condition: If text is valid JSON representing a list, returns that list. If text is not valid JSON or does not represent a list, raises an exception.
# [INFO]

def _llm_rerank(funcs_info: list[dict],
                source_lines: list[str],
                filepath: str,
                issue: str,
                top_k: int,
                llm_client: Any,
                model: str) -> list[str] | None:
    func_list = _build_func_list_text(funcs_info, source_lines)
    user_msg = _LLM_USER_TMPL.format(
        issue=issue[:3000],
        filepath=filepath,
        func_list=func_list,
        top_k=top_k,
    )
    messages = [
        {"role": "system", "content": _LLM_SYSTEM},
        {"role": "user", "content": user_msg},
    ]
    for attempt in range(3):
        text = ""
        try:
            response = llm_client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=256,
                temperature=0.0,
            )
            text = response.choices[0].message.content.strip()
            names = _parse_json_response(text)
            if not isinstance(names, list) or not all(
                isinstance(name, str) and name.strip() for name in names
            ):
                raise ValueError("LLM rerank response must be a JSON array of non-empty function names")
            return [name.strip() for name in names]
        except Exception as exc:
            logger.warning("LLM rerank attempt %d failed: %s", attempt + 1, exc)
            if attempt < 2:
                messages = messages + [
                    {"role": "assistant", "content": text},
                    {"role": "user", "content": (
                        "Return only valid JSON: an array of non-empty function-name strings. "
                        "Do not include Markdown, tags, or prose."
                    )},
                ]
                time.sleep(5 * (attempt + 1))
    return None

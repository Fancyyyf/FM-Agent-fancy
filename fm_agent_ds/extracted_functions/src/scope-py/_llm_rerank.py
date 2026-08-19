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

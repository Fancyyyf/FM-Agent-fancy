def _parse_spec_check_json(response):
    """Parse and validate the spec-check model structured JSON verdict."""
    try:
        data = _load_spec_check_json(response)
    except json.JSONDecodeError as exc:
        raise ValueError(f"spec-check response is not valid JSON: {exc}") from exc

    if not isinstance(data, dict):
        raise ValueError("spec-check JSON must be an object")

    required = ("verdict", "counterexample", "offending_statements", "reason")
    missing = [field for field in required if field not in data]
    if missing:
        raise ValueError("spec-check JSON missing required field(s): " + ", ".join(missing))

    verdict = data.get("verdict")
    if isinstance(verdict, str):
        verdict = verdict.upper()
    if verdict not in ("MATCH", "MISMATCH"):
        raise ValueError("spec-check JSON verdict must be MATCH or MISMATCH")

    counterexample = data.get("counterexample")
    offending_statements = data.get("offending_statements")
    reason = data.get("reason")

    if counterexample is not None and not isinstance(counterexample, str):
        raise ValueError("spec-check JSON field counterexample must be a string or null")
    if offending_statements is not None and not isinstance(offending_statements, str):
        raise ValueError("spec-check JSON field offending_statements must be a string or null")
    if not isinstance(reason, str):
        raise ValueError("spec-check JSON field reason must be a string")

    def _nonempty_string(value):
        return isinstance(value, str) and bool(value.strip())

    data["verdict"] = verdict

    if verdict == "MISMATCH":
        missing = [
            name for name, value in (
                ("counterexample", counterexample),
                ("offending_statements", offending_statements),
                ("reason", reason),
            )
            if not _nonempty_string(value)
        ]
        if missing:
            raise ValueError(
                "spec-check MISMATCH JSON missing non-empty field(s): " + ", ".join(missing)
            )
        data["counterexample"] = counterexample.strip()
        data["offending_statements"] = offending_statements.strip()
        data["reason"] = reason.strip()
        return True, data["offending_statements"], data["reason"], data

    if _nonempty_string(counterexample) or _nonempty_string(offending_statements):
        raise ValueError(
            "spec-check MATCH JSON must not include counterexample or offending_statements"
        )
    data["counterexample"] = None
    data["offending_statements"] = None
    data["reason"] = reason.strip()
    return False, None, None, data

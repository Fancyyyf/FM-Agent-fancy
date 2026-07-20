# [SPEC]
# Unit: src/prompts-py/_parse_spec_check_json.py
#
# _parse_spec_check_json(response)
#
# Pre-condition:
#   - response is a non-empty string
#
# Post-condition:
#   - Raises ValueError if response is not valid JSON text
#   - Raises ValueError if the parsed JSON value is not a mapping (dict)
#   - Raises ValueError if the parsed mapping does not contain all of the required keys: "verdict", "counterexample", "offending_statements", "reason"
#   - Raises ValueError if the "verdict" value, after conversion to uppercase, is neither "MATCH" nor "MISMATCH"
#   - Raises ValueError if "counterexample" is present and not null-valued but is not a string
#   - Raises ValueError if "offending_statements" is present and not null-valued but is not a string
#   - Raises ValueError if "reason" is not a string value
#   - For "MISMATCH" verdict: raises ValueError if any of counterexample, offending_statements, or reason is empty or consists only of whitespace; otherwise returns a tuple (True, offending_statements_with_leading_trailing_whitespace_removed, reason_with_whitespace_removed, data) where data is the parsed dict with verdict uppercased, counterexample set to the stripped value, offending_statements set to the stripped value, and reason set to the stripped value
#   - For "MATCH" verdict: raises ValueError if counterexample or offending_statements is a non-empty string; otherwise returns a tuple (False, None, None, data) where data is the parsed dict with verdict uppercased, counterexample set to None, offending_statements set to None, and reason set to its stripped value
# [SPEC]

# [INFO]
# _load_spec_check_json(response)
#   Pre-condition: response is a string
#   Post-condition: Returns the Python value produced by deserializing response as JSON text; raises json.JSONDecodeError if response is not valid JSON
# [INFO]

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

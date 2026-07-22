# [SPEC]
# Unit: src/pipeline_setup-py/_phase_plan_schema_errors.py
#
# _phase_plan_schema_errors(phases_path) -> list[str]
#
# Pre-condition:
#   - phases_path is a string.
#
# Post-condition:
#   - Returns a list of human-readable error message strings.
#
#   - When the file at phases_path cannot be read (any OS error including absent file or
#     permission denied), the returned list is non-empty and contains a single element
#     describing the OS error.
#
#   - When the file at phases_path is readable but its content is not valid JSON, the
#     returned list is non-empty and contains a single element describing the JSON parse
#     error.
#
#   - When the file is readable and its content is valid JSON, the returned list is empty if
#     and only if the decoded JSON structure satisfies all of the following requirements:
#       a) The top-level decoded value is a JSON object (dict).
#       b) The object has a key "phases" whose value is a JSON array.
#       c) Every element of the "phases" array is a JSON object.
#       d) Every object in "phases" has a key "modules" whose value is a JSON array.
#       e) Every element of a "modules" array is a JSON object.
#       f) Every object in "modules" has a key "source_files" whose value is a JSON array.
#       g) Every element of a "source_files" array is a JSON string.
#
#   - When the decoded JSON violates any requirement from (a) through (g), the returned
#     list is non-empty. Each element of the list describes exactly one violation using
#     JSON-path notation (zero-based array indices in brackets). When a module object
#     has a non-empty "name" key, violation messages for that module include the name
#     value for identification.
#
#   - The function does not modify the file at phases_path or any other persistent state.
#   - The function always returns within finite time regardless of inputs.
# [SPEC]

def _phase_plan_schema_errors(phases_path):
    """Return human-readable schema errors for phases.json."""
    try:
        with open(phases_path, "r") as f:
            data = json.load(f)
    except OSError as exc:
        return [f"phases.json could not be read: {exc}"]
    except json.JSONDecodeError as exc:
        return [f"phases.json is not valid JSON: {exc}"]

    if not isinstance(data, dict):
        return ["the top-level value must be an object"]

    phases = data.get("phases")
    if not isinstance(phases, list):
        return ['top-level field "phases" must be an array']

    errors = []
    for phase_index, phase in enumerate(phases):
        phase_path = f"phases[{phase_index}]"
        if not isinstance(phase, dict):
            errors.append(f"{phase_path} must be an object")
            continue

        modules = phase.get("modules")
        if not isinstance(modules, list):
            errors.append(f"{phase_path}.modules must be an array")
            continue

        for module_index, module in enumerate(modules):
            module_path = f"{phase_path}.modules[{module_index}]"
            if not isinstance(module, dict):
                errors.append(f"{module_path} must be an object")
                continue

            module_name = module.get("name", "")
            context = (
                f"{module_path} ({module_name!r})"
                if module_name
                else module_path
            )

            if "source_files" not in module:
                errors.append(f"{context}.source_files is missing")
                continue

            source_files = module["source_files"]
            if not isinstance(source_files, list):
                errors.append(f"{context}.source_files must be an array")
                continue

            for source_index, source_file in enumerate(source_files):
                if not isinstance(source_file, str):
                    errors.append(
                        f"{context}.source_files[{source_index}] must be a string"
                    )

    return errors

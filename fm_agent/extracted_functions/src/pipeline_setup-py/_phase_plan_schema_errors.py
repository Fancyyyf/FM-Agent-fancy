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

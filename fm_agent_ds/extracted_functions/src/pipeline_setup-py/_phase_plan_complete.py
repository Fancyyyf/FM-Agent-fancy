def _phase_plan_complete(work_dir):
    """Return True only if phases.json exists and matches the required schema."""
    phases_path = os.path.join(work_dir, "phases.json")
    return not _phase_plan_schema_errors(phases_path)

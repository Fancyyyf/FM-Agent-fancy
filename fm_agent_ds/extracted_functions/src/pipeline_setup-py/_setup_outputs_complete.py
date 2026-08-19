def _setup_outputs_complete(work_dir):
    """Return True when both phase plan and domain context are complete."""
    return _phase_plan_complete(work_dir) and _domain_context_complete(work_dir)

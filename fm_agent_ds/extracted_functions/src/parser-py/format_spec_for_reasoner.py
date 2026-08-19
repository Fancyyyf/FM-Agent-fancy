def format_spec_for_reasoner(spec):
    """Rebuild reasoner-facing spec text from one .spec.json object."""
    return (
        f"{spec.get('signature', '')}\n\n"
        f"Pre-condition:\n{spec.get('pre_condition', '')}\n\n"
        f"Post-condition:\n{spec.get('post_condition', '')}"
    )

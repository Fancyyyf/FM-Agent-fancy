def _load_phases(proj_dir):
    """Load phases.json from the project root."""
    phases_path = os.path.join(proj_dir, "phases.json")
    with open(phases_path, "r") as f:
        return json.load(f)

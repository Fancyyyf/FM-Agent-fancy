def _strip_star(d):
    """Strip leading '*' from dict keys (lucentia opencode-trace streaming convention)."""
    if not isinstance(d, dict):
        return d
    return {(k[1:] if k.startswith("*") else k): v for k, v in d.items()}

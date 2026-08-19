def _normalize_spec_dict(spec):
    """Keep only fields supported by a .spec.json sidecar."""
    return {
        "signature": spec.get("signature", ""),
        "pre_condition": spec.get("pre_condition", ""),
        "post_condition": spec.get("post_condition", ""),
    }

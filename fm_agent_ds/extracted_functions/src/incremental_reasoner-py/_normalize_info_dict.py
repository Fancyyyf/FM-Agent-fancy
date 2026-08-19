def _normalize_info_dict(info):
    """Keep only fields supported by a .info.json sidecar."""
    callees = info.get("callees", [])
    if not isinstance(callees, list):
        raise ValueError("info JSON field callees must be an array")
    return {
        "callees": [
            {
                "name": callee.get("name", ""),
                "signature": callee.get("signature", ""),
                "pre_condition": callee.get("pre_condition", ""),
                "post_condition": callee.get("post_condition", ""),
            }
            for callee in callees
            if isinstance(callee, dict)
        ]
    }

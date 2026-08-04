def utc_now_iso():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

def new_event_id(prefix="evt"):
    return f"{prefix}_{uuid.uuid4().hex}"

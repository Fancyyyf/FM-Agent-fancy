def _stable_user_id():
    return settings.inject.id or _DEFAULT_INJECT_USER_ID

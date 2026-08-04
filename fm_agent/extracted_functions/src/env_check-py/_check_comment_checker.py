def _check_comment_checker():
    if not os.path.exists(OH_MY_OPENAGENT_CONFIG):
        return False, f"oh-my-openagent config not found at {OH_MY_OPENAGENT_CONFIG}"

    try:
        with open(OH_MY_OPENAGENT_CONFIG, "r") as f:
            cfg = json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        return False, f"Failed to read {OH_MY_OPENAGENT_CONFIG}: {e}"

    if "comment-checker" not in cfg.get("disabled_hooks", []):
        return False, (
            "comment-checker hook is NOT disabled. FM-Agent writes function "
            "specifications as comment blocks, which the comment-checker may "
            "intercept, wasting tokens or deleting specs. Add "
            '"disabled_hooks": ["comment-checker"] to ' + OH_MY_OPENAGENT_CONFIG
        )

    return True, None

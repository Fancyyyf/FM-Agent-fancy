def _check_oh_my_openagent():
    import subprocess
    try:
        subprocess.run(
            ["bunx", "oh-my-openagent", "--version"],
            capture_output=True, text=True, timeout=10,
        )
        return True, None
    except Exception:
        return False, "oh-my-openagent is not installed (bunx unavailable or timed out)"

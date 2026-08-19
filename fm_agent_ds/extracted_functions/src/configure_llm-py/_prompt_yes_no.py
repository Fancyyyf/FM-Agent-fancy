def _prompt_yes_no(prompt: str, default: bool = True) -> bool:
    hint = "Y/n" if default else "y/N"
    choice = _prompt(f"{prompt} [{hint}]").lower()
    if not choice:
        return default
    if choice in ("y", "yes"):
        return True
    if choice in ("n", "no"):
        return False
    raise ConfigWizardError("Please answer yes or no.")

def _caller_module(path: str) -> str:
    base = os.path.basename(path)
    dot = base.rfind(".")
    return base[:dot] + "-" + base[dot + 1 :] if dot > 0 else base

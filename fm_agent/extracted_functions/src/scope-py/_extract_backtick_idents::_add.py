    def _add(token: str) -> None:
        t = token.lower().strip('_')
        if len(t) >= 2 and t not in _PY_KEYWORDS and t not in _STOP:
            result.add(t)

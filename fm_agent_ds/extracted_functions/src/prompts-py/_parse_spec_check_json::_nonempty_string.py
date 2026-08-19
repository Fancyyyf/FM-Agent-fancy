    def _nonempty_string(value):
        return isinstance(value, str) and bool(value.strip())

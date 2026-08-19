    def row(label, b):
        return [
            label,
            _fmt_tokens(b.get("input", 0)),
            _fmt_tokens(b.get("cache_read", 0)),
            _fmt_tokens(b.get("cache_write", 0)),
            _fmt_tokens(b.get("output", 0)),
        ]

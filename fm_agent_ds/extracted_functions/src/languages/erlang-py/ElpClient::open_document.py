    def open_document(self, path: str, source: str | None = None):
        document = Path(path).resolve()
        if source is None:
            source = document.read_text(encoding="utf-8", errors="replace")
        self.notify(
            "textDocument/didOpen",
            {
                "textDocument": {
                    "uri": document.as_uri(),
                    "languageId": "erlang",
                    "version": 1,
                    "text": source,
                }
            },
        )

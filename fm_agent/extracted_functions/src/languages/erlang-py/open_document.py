# [SPEC]
# Unit: src/languages/erlang-py/open_document.py
#
# ElpClient.open_document(self, path: str, source: str | None = None) -> None
#
# Pre-condition:
#   - self is an ElpClient instance with an open LSP communication channel to the
#     backend
#   - path is a non-empty string
#
# Post-condition:
#   - Sends a `textDocument/didOpen` LSP notification to the backend for the
#     document at the absolute, resolved path derived from path
#   - The notification URI is the `file://` URI of the resolved path
#   - When source is a non-None string, the notification carries source as the
#     document text
#   - When source is None, the notification carries the file contents at the
#     resolved path as the document text
#   - The document is registered with language identifier "erlang" and version 1
#   - Returns None upon successful notification delivery
#   - Raises an exception when source is None and the file at the resolved path
#     cannot be read, or when the LSP communication channel is not open
# [SPEC]

# [INFO]
# self.notify(method: str, params: dict) -> None
#   Pre-condition: method is a non-empty string identifying the LSP notification;
#     params is a dict containing the notification parameters
#   Post-condition: Sends an LSP notification to the backend with the given method
#     and params; does not wait for a response
# [INFO]

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

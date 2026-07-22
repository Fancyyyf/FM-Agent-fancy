# [SPEC]
# Unit: src/languages/erlang.py
#
# ElpClient.open_document(self, path: str, source: str | None = None)
#
# Pre-condition:
#   - self is an ElpClient whose underlying JSON-RPC communication channel
#     is open and writable
#   - path is a non-empty string identifying a filesystem path
#   - When source is None, path must resolve to an existing, readable
#     text file
#
# Post-condition:
#   - Transmits a "textDocument/didOpen" notification to the ELP server
#     whose textDocument field is a dict containing:
#       - uri: the absolute file:// URI representing the path argument
#       - languageId: "erlang"
#       - version: 1
#       - text: source when source is provided; otherwise the UTF-8 text
#         content of the file at path
#   - When source is None and the file at path cannot be read, the
#     underlying IOError propagates to the caller
# [SPEC]

# [INFO]
# notify(self, method: str, params: dict | list | None = None)
#   Pre-condition: The underlying JSON-RPC communication channel is open
#     and writable
#   Post-condition: A JSON-RPC 2.0 notification message (a message
#     without an id field) carrying the given method and params is
#     transmitted to the ELP server; when params is None, the transmitted
#     params is an empty dict
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

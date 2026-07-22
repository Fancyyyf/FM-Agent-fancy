# [SPEC]
# Unit: src/languages/erlang.py
#
# ElpClient.initialize(self, bootstrap_path: str, bootstrap_source: str | None = None)
#
# Pre-condition:
#   - self is an ElpClient whose __enter__ has been called (ELP subprocess is
#     running, stdin/stdout pipes are open, and the JSON-RPC message reader
#     thread is active)
#   - bootstrap_path is a non-empty string identifying a filesystem path; if
#     bootstrap_source is None, bootstrap_path must resolve to an existing,
#     readable text file
#   - bootstrap_source, when provided, is a string containing the document
#     content to use instead of reading from bootstrap_path
#
# Post-condition:
#   - Completes the LSP initialization handshake: sends the "initialize"
#     request with client capabilities, then sends the "initialized"
#     notification
#   - Opens the document at bootstrap_path on the server with the text content
#     matching bootstrap_source (or the file contents of bootstrap_path when
#     bootstrap_source is None)
#   - Blocks until the server's reported status indicates it has reached a
#     running state, or raises TimeoutError when that does not occur within
#     self.timeout seconds measured from the call entry
#   - Returns the "serverInfo" sub-dict from the server's "initialize"
#     response, or None when the response is missing, is not a dict, or does
#     not contain a "serverInfo" key
#   - Raises RuntimeError when the ELP subprocess is not running (stdin
#     unavailable) or the JSON-RPC channel encounters an unrecoverable error
#   - Raises TimeoutError when the server fails to reach the running state
#     within the deadline or the subprocess stops producing messages
# [SPEC]

# [INFO]
# request(self, method: str, params: dict | list | None = None)
#   Pre-condition: self._proc.stdin is open and writable; method is a
#     non-empty string; params, when provided, is a JSON-serializable
#     dict or list
#   Post-condition: Sends a JSON-RPC request with a unique monotonically
#     increasing integer id and the given method and params (defaulting to
#     {} when params is None); blocks until the matching response arrives;
#     returns the "result" field of the response; raises RuntimeError when
#     the server responds with a non-ContentModified error; raises
#     TimeoutError when the response does not arrive within self.timeout
#     seconds; retries automatically up to a fixed maximum on
#     ContentModified errors and raises RuntimeError when all retries are
#     exhausted
# [SPLIT]
# notify(self, method: str, params: dict | list | None = None)
#   Pre-condition: self._proc.stdin is open and writable; method is a
#     non-empty string; params, when provided, is a JSON-serializable
#     dict or list
#   Post-condition: Sends a JSON-RPC notification with the given method
#     and params (defaulting to {} when params is None) to the ELP server;
#     no response is expected or awaited; raises RuntimeError when the
#     client is not running
# [SPLIT]
# open_document(self, path: str, source: str | None = None)
#   Pre-condition: self._proc.stdin is open and writable; path is a
#     non-empty string identifying a filesystem path; when source is None,
#     path must resolve to an existing readable text file
#   Post-condition: The document at path is registered with the ELP server
#     via a "textDocument/didOpen" notification carrying the resolved
#     absolute URI, language identifier "erlang", version 1, and the text
#     content (source when provided, otherwise the UTF-8 contents of the
#     file at path); when source is None and the file cannot be read, the
#     underlying IOError propagates
# [SPLIT]
# _next_message(self, deadline: float)
#   Pre-condition: deadline is a point in time expressed as a
#     monotonic clock value; the message reader thread is active and
#     writing to the internal message queue
#   Post-condition: Returns the next pending parsed JSON-RPC response or
#     notification message from the server as a dict before deadline
#     expires; raises TimeoutError when the deadline is reached before a
#     message arrives; raises RuntimeError when the reader thread
#     terminated with an exception
# [SPLIT]
# _handle_server_message(self, message: dict)
#   Pre-condition: message is a dict representing a parsed JSON-RPC
#     message received from the server
#   Post-condition: If the message method is "elp/status", updates
#     self._status to the value of params.status (retaining the previous
#     value when params is absent or lacks a "status" key); when the
#     message carries both an "id" and a "method" (a server request),
#     sends back a JSON-RPC response whose "result" value satisfies the
#     server's expectation for that request method; when the message has
#     no "id" (a notification), no response is sent
# [INFO]

    def initialize(self, bootstrap_path: str, bootstrap_source: str | None = None):
        result = self.request(
            "initialize",
            {
                "processId": os.getpid(),
                "clientInfo": {"name": "fm-agent", "version": "0.1.0"},
                "rootUri": self.root_uri,
                "workspaceFolders": [
                    {"uri": self.root_uri, "name": os.path.basename(self.proj_dir)}
                ],
                "capabilities": {
                    "experimental": {"serverStatusNotification": True},
                    "workspace": {"configuration": True, "workspaceFolders": True},
                    "textDocument": {
                        "documentSymbol": {
                            "dynamicRegistration": False,
                            "hierarchicalDocumentSymbolSupport": True,
                        }
                    },
                },
            },
        )
        server_info = (result or {}).get("serverInfo") if isinstance(result, dict) else None
        self.notify("initialized")
        self.open_document(bootstrap_path, bootstrap_source)

        deadline = time.monotonic() + self.timeout
        while str(self._status).lower() != "running":
            self._handle_server_message(self._next_message(deadline))
        return server_info

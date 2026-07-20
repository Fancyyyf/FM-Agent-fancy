# [SPEC]
# Unit: src/languages/erlang-py/initialize.py
#
# ElpClient.initialize(bootstrap_path: str, bootstrap_source: str | None = None) -> dict | None
#
# Pre-condition:
#   - self is an ElpClient instance with a running LSP backend process and an open JSON-RPC
#     communication channel
#   - self.root_uri is a non-empty string, self.proj_dir is a non-empty string, and
#     self.timeout is a positive number
#   - bootstrap_path is a non-empty string
#
# Post-condition:
#   - Sends an LSP "initialize" JSON-RPC request containing the process PID, client identification
#     ("fm-agent", "0.1.0"), the root URI, a workspace folder entry with the root URI and the
#     base name of self.proj_dir, and a capabilities object advertising hierarchical documentSymbol
#     support with server-status and workspace-configuration notifications enabled
#   - Sends an "initialized" JSON-RPC notification after receiving the initialization response
#   - Opens the document at bootstrap_path in the LSP backend, providing bootstrap_source as the
#     document text when bootstrap_source is a non-None string, or signalling the backend to read
#     the file from disk when bootstrap_source is None
#   - Blocks, processing every server message received, until the server-reported status string
#     is equal to "running" (compared case-insensitively)
#   - Raises an exception when a server message cannot be retrieved before an elapsed wall-clock
#     duration of self.timeout seconds since the call, or when a JSON-RPC communication failure occurs
#   - Returns the value of the "serverInfo" key from the initialization response dict when the
#     response is a dict and the key exists; returns None when the response is not a dict or does
#     not contain a "serverInfo" key
# [SPEC]

# [INFO]
# self.request(method: str, params: dict) -> dict | None
#   Pre-condition: method is a non-empty string, params is a dict, and the LSP backend channel is open
#   Post-condition: Sends a JSON-RPC request to the LSP backend with the given method and params;
#     returns the response body as a dict when the request succeeds and produces a response;
#     returns None when the request fails or produces no response body
# [SPLIT]
# self.notify(method: str) -> None
#   Pre-condition: method is a non-empty string and the LSP backend channel is open
#   Post-condition: Sends a JSON-RPC notification with the given method to the LSP backend;
#     does not wait for or return a response
# [SPLIT]
# self.open_document(path: str, source: str | None) -> None
#   Pre-condition: path is a non-empty string and the LSP backend channel is open
#   Post-condition: Opens the document at path in the LSP backend; when source is a non-None string,
#     provides that text as the initial document content; when source is None, the backend reads
#     the file from disk at path
# [SPLIT]
# self._handle_server_message(msg: dict) -> None
#   Pre-condition: msg is a non-empty dict representing a JSON-RPC message received from the LSP
#     backend
#   Post-condition: Processes the server message, updating internal client state including
#     self._status to reflect the server state reported in the message
# [SPLIT]
# self._next_message(deadline: float) -> dict
#   Pre-condition: deadline is a monotonic-time value in seconds and the LSP backend channel is open
#   Post-condition: Blocks until a message is received from the LSP backend and returns it as a dict;
#     raises an exception when no message arrives before the wall-clock monotonic time exceeds deadline
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

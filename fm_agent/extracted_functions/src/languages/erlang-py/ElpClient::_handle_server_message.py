# [SPEC]
# Unit: src/languages/erlang.py
#
# ElpClient._handle_server_message(self, message: dict)
#
# Pre-condition:
#   - self is an ElpClient whose __enter__ has been called (ELP subprocess
#     is running and the JSON-RPC message reader thread is active)
#   - message is a dict representing a parsed JSON-RPC message received
#     from the ELP server
#
# Post-condition:
#   - When message.method is "elp/status", updates self._status to the
#     value of message.params.status; if the params dict is absent or lacks
#     a "status" key, self._status is unchanged
#   - When message lacks an "id" field, or message.method is absent or
#     falsy, no response is sent (the message is treated as a notification)
#   - When message carries both a non-empty "method" and an "id" (a server
#     request), sends a JSON-RPC response with jsonrpc "2.0" and the same
#     id; the result value satisfies the protocol-defined expectation for
#     that method:
#     - For workspace configuration queries: result is a list whose length
#       equals the number of requested configuration items, each element
#       being null
#     - For workspace folder queries: result is a singleton list containing
#       the workspace-folder descriptor with the project root URI and
#       directory name
#     - For workspace edit requests: result indicates the edit was declined
#       (applied is false)
#     - For any other method the client does not handle: result is null
# [SPEC]

# [INFO]
# _send(self, message: dict)
#   Pre-condition: self is an ElpClient whose stdin pipe to the ELP
#     subprocess is open and writable; message is a dict representing a
#     well-formed JSON-RPC message to be delivered to the server
#   Post-condition: The JSON-serialized form of message has been written
#     to the subprocess's stdin, following the LSP transport protocol
#     framing; the server will receive the complete message as its next
#     input
# [INFO]

    def _handle_server_message(self, message: dict):
        method = message.get("method")
        params = message.get("params")
        if params is None:
            params = {}
        if method == "elp/status":
            self._status = params.get("status")
        if "id" not in message or not method:
            return

        if method == "workspace/configuration":
            result = [None for _ in params.get("items", [])]
        elif method == "workspace/workspaceFolders":
            result = [{"uri": self.root_uri, "name": os.path.basename(self.proj_dir)}]
        elif method == "workspace/applyEdit":
            result = {"applied": False}
        else:
            result = None
        self._send({"jsonrpc": "2.0", "id": message["id"], "result": result})

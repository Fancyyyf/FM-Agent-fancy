# [SPEC]
# Unit: src/languages/erlang-py/request.py
#
# ElpClient._handle_server_message(self, message: dict) -> None
#
# Pre-condition:
#   - self is an ElpClient instance with a JSON-RPC communication channel to an
#     LSP backend and attributes root_uri, proj_dir
#   - message is a non-empty dict representing a parsed JSON-RPC message received
#     from the LSP backend
#
# Post-condition:
#   - When message lacks an "id" field or has a falsy "method" field (a
#     server notification), returns without sending a response, having processed
#     any side-effectful notification content
#   - When message contains a method whose name matches a known status-reporting
#     pattern, updates self._status to the value of the "status" key in the
#     message params, defaulting to None when the key is absent or params is
#     absent
#   - When message contains both a truthy "id" field and a truthy "method" field
#     (a server-initiated request), sends a JSON-RPC 2.0 response via the
#     client's communication channel:
#     * The response "id" field equals message["id"]
#     * The response "result" field has a value determined by the method's
#       category: configuration-query methods return a list whose length matches
#       the requested items count; folder-query methods return a list containing
#       a single workspace entry with the client's root URI and the base name of
#       the project directory; edit-request methods return a dict whose
#       application-related key is set to a falsy value; any unrecognized method
#       returns None
# [SPEC]

# [INFO]
# self._send(self, data: dict) -> None
#   Pre-condition: data is a dict representing a JSON-RPC message to be
#     serialized and transmitted to the LSP backend
#   Post-condition: The message is transmitted to the backend; raises an
#     exception on communication failure
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

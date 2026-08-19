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

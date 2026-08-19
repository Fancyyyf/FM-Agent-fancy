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

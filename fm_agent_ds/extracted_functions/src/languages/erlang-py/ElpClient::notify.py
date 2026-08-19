    def notify(self, method: str, params: dict | list | None = None):
        actual_params = {} if params is None else params
        self._send({"jsonrpc": "2.0", "method": method, "params": actual_params})

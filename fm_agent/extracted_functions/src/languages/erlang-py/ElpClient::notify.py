# [SPEC]
# Unit: src/languages/erlang.py
#
# ElpClient.notify(self, method: str, params: dict | list | None = None)
#
# Pre-condition:
#   - self._proc is not None and self._proc.stdin is open and writable
#   - method is a non-empty string identifying a known LSP notification method
#   - params, when not None, is a JSON-serializable dict or list
#
# Post-condition:
#   - Transmits a JSON-RPC 2.0 notification message to the ELP subprocess's
#     standard input
#   - The transmitted message is a JSON object containing "jsonrpc": "2.0",
#     "method" set to the method argument, and no "id" member
#   - When params is None, the transmitted "params" is an empty JSON object;
#     otherwise "params" is set to the params argument value unchanged
#   - No response from the server is awaited
#   - Raises RuntimeError when the ELP subprocess is not running or stdin
#     is unavailable
# [SPEC]

# [INFO]
# _send(self, message: dict)
#   Pre-condition: self._proc is not None and self._proc.stdin is open and
#     writable; message is a JSON-serializable dict
#   Post-condition: The message is serialized to UTF-8 JSON, framed with a
#     Content-Length header, and written to the ELP subprocess's standard input
#     stream; raises RuntimeError when the subprocess is not running or stdin
#     is unavailable
# [INFO]

    def notify(self, method: str, params: dict | list | None = None):
        actual_params = {} if params is None else params
        self._send({"jsonrpc": "2.0", "method": method, "params": actual_params})

# [SPEC]
# Unit: fm_agent/extracted_functions/src/languages/erlang-py/notify.py
#
# notify(self, method: str, params: dict | list | None = None) -> None
#
# Pre-condition:
#   - method is a non-empty string identifying the LSP notification method to invoke
#   - The underlying communication channel to the LSP backend is open
#
# Post-condition:
#   - A JSON-RPC 2.0 notification message is sent to the LSP backend via the
#     underlying communication channel
#   - The transmitted message is a dict containing exactly the keys: "jsonrpc" with
#     value "2.0", "method" with value equal to the method parameter, and "params"
#     with value equal to the params parameter when params is not None, or an empty
#     dict when params is None
#   - The transmitted message contains no "id" key
#   - Returns None without waiting for any server response
#   - Raises an exception when the underlying communication channel cannot deliver
#     the message
# [SPEC]

# [INFO]
# _send(self, message: dict) -> None
#   Pre-condition: The underlying communication channel to the LSP backend is open
#   Post-condition: The given dict is serialized as a JSON-RPC message and sent to
#     the LSP backend; raises an exception when the channel cannot deliver the message
# [INFO]

    def notify(self, method: str, params: dict | list | None = None):
        actual_params = {} if params is None else params
        self._send({"jsonrpc": "2.0", "method": method, "params": actual_params})

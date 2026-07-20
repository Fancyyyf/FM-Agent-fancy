# [SPEC]
# Unit: src/languages/erlang-py/__init__.py
#
# __init__(self, stream: BinaryIO, messages: queue.Queue)
#
# Pre-condition:
#   - stream is an open, readable binary stream (typically the stdout pipe of a subprocess)
#   - messages is a Queue instance that supports concurrent enqueue from a background thread
#
# Post-condition:
#   - self is initialized as a daemon thread named "fm-agent-elp-reader"
#   - self._stream references the provided binary stream, to be consumed character-by-character
#     in the thread's run() method
#   - self._messages references the provided queue, to which deserialized JSON-RPC message
#     objects will be appended during the thread's run() method
#   - The thread has NOT been started; the caller must invoke .start() to begin reading
# [SPEC]

# [INFO]
# (no callees)
# [INFO]

    def __init__(self, stream: BinaryIO, messages: queue.Queue):
        super().__init__(name="fm-agent-elp-reader", daemon=True)
        self._stream = stream
        self._messages = messages

    def __init__(self, stream: BinaryIO, messages: queue.Queue):
        super().__init__(name="fm-agent-elp-reader", daemon=True)
        self._stream = stream
        self._messages = messages

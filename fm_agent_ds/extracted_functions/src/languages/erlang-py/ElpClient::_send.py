    def _send(self, message: dict):
        if self._proc is None or self._proc.stdin is None:
            raise RuntimeError("ELP client is not running")
        payload = json.dumps(message, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        frame = f"Content-Length: {len(payload)}\r\n\r\n".encode("ascii") + payload
        with self._write_lock:
            self._proc.stdin.write(frame)
            self._proc.stdin.flush()

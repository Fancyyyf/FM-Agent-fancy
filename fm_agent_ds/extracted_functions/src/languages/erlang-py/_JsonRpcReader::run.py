    def run(self):
        try:
            while True:
                headers = {}
                while True:
                    line = self._stream.readline()
                    if not line:
                        raise EOFError("ELP closed its stdout")
                    if line in (b"\r\n", b"\n"):
                        break
                    name, separator, value = line.decode("ascii", "replace").partition(":")
                    if separator:
                        headers[name.strip().lower()] = value.strip()
                length = int(headers["content-length"])
                payload = self._stream.read(length)
                if len(payload) != length:
                    raise EOFError("ELP returned a truncated JSON-RPC payload")
                self._messages.put(json.loads(payload.decode("utf-8")))
        except BaseException as exc:
            self._messages.put(exc)

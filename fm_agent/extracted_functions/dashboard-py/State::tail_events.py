    def tail_events(self):
        if not self.events_path.exists():
            return
        size = self.events_path.stat().st_size
        if size < self._events_offset:
            # file truncated/rotated
            self._events_offset = 0
        if size == self._events_offset:
            return
        with open(self.events_path, "r", encoding="utf-8") as f:
            f.seek(self._events_offset)
            for line in f:
                if not line.strip():
                    continue
                try:
                    ev = json.loads(line)
                except Exception:
                    continue
                self._ingest_event(ev)
            self._events_offset = f.tell()

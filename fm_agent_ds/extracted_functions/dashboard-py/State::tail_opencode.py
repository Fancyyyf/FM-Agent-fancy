    def tail_opencode(self):
        if not self.opencode_dir.exists():
            return
        for path in sorted(self.opencode_dir.glob("*.jsonl")):
            name = path.name
            try:
                size = path.stat().st_size
            except OSError:
                continue
            off = self._opencode_offsets.get(name, 0)
            if size < off:
                off = 0
            if size == off:
                continue
            with open(path, "r", encoding="utf-8") as f:
                f.seek(off)
                for line in f:
                    if not line.strip():
                        continue
                    try:
                        rec = json.loads(line)
                    except Exception:
                        continue
                    self._ingest_opencode(rec, name)
                self._opencode_offsets[name] = f.tell()

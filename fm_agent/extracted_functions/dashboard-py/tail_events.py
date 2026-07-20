# [SPEC]
# Unit: fm_agent/extracted_functions/dashboard-py/tail_events.py
#
# State.tail_events(self) -> None
#
# Pre-condition:
#   - self.events_path is a Path object pointing to a JSONL file where each
#     non-blank line is a valid JSON object.
#   - self._events_offset is a non-negative integer tracking the byte
#     position up to which the file has already been processed by previous
#     calls.
#
# Post-condition:
#   - Every non-blank line in self.events_path that was written after the
#     byte position recorded in self._events_offset at call time is parsed
#     as a JSON object and passed to self._ingest_event.
#   - Lines that are blank or cannot be parsed as valid JSON are silently
#     skipped and do not prevent processing of subsequent lines.
#   - self._events_offset is updated to the file's end byte position after
#     all newly written lines have been read.
#   - If self.events_path does not exist, the function returns immediately
#     and no state is modified.
#   - If the file's current byte size is smaller than self._events_offset
#     (indicating truncation or rotation), self._events_offset is reset to
#     0 before reading, causing the entire file to be reprocessed.
#   - If the file's current byte size equals self._events_offset (no new
#     data written since the last call), the function returns immediately
#     and no state is modified.
# [SPEC]

# [INFO]
# (no callees)
# [INFO]

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

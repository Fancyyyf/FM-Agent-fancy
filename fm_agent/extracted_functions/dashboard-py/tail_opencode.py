# [SPEC]
# Unit: fm_agent/extracted_functions/dashboard-py/tail_opencode.py
#
# tail_opencode(self) -> None
#
# Pre-condition:
#   - self is an initialized State with a project directory.
#   - self.opencode_dir is a pathlib.Path that may or may not exist.
#   - self._opencode_offsets is a dict mapping filenames to integer byte offsets.
#
# Post-condition:
#   - If self.opencode_dir does not exist, returns immediately with no side effects.
#   - All files ending in ".jsonl" in self.opencode_dir are visited in ascending
#     lexicographic order of filename.
#   - For each such file: any content appended since the previous call to
#     tail_opencode is consumed; if no previous offset was recorded for the file,
#     all content is consumed.
#   - If a file has fewer bytes than its previously recorded offset (indicating
#     truncation or rotation), the offset is silently reset to zero before reading.
#   - If a file has no new content since the last recorded offset, it is skipped.
#   - Every non-empty line in the new content that decodes as a valid JSON object
#     is ingested by the State; lines that fail JSON decoding are silently skipped.
#   - After processing all files, the byte position immediately after the last
#     consumed byte in each file is recorded so that a subsequent call to
#     tail_opencode only reads content appended after that point.
#   - The State's aggregated metrics derived from OpenCode trace data are updated
#     to reflect all newly ingested records.
# [SPEC]

# [INFO]
# _ingest_opencode(rec, name) -> None
#   Pre-condition: rec is a dict parsed from a single line of a JSONL trace file.
#     name is a string identifying the source JSONL filename.
#   Post-condition: The State's internal aggregated metrics (token usage, cost,
#     cache hit rate, stage progress, and any other dashboard-displayed data)
#     are updated to include the information contained in rec.
# [INFO]

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

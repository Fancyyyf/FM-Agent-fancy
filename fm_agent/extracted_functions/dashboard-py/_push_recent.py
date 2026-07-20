# [SPEC]
# Unit: fm_agent/extracted_functions/dashboard-py/_push_recent.py
#
# State._push_recent(self, ts, stage, status, summary) -> None
#
# Pre-condition:
#   - self is an initialized State with a bounded recent_events collection
#     that has a fixed maximum capacity.
#   - ts is a datetime or None.
#   - stage, status, and summary are strings.
#
# Post-condition:
#   - A 4-tuple (when_str, stage, status, summary) is present at the most
#     recently added position of self.recent_events, where when_str is the
#     "HH:MM:SS"-formatted string of ts if ts is not None, or "" (empty
#     string) if ts is None.
#   - If self.recent_events was at maximum capacity before the call, the
#     chronologically oldest entry is evicted.
#   - Every other entry in self.recent_events retains its relative
#     insertion order (all existing entries shift one position toward
#     the eviction boundary).
#   - self.recent_events does not grow beyond its fixed capacity.
#   - No value other than recent_events of self is modified.
# [SPEC]

# [INFO]
# (no callees)
# [INFO]

    def _push_recent(self, ts, stage, status, summary):
        when = ts.strftime("%H:%M:%S") if ts else ""
        self.recent_events.appendleft((when, stage, status, summary))

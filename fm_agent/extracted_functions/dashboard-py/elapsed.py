# [SPEC]
# Unit: fm_agent/extracted_functions/dashboard-py/elapsed.py
#
# elapsed(self) -> Optional[float]
#
# Pre-condition:
#   - self.first_event_time is either None or a timezone-aware datetime
#     representing when the earliest recorded event occurred
#   - self.last_event_time is either None or a timezone-aware datetime
#     representing when the most recent recorded event occurred
#
# Post-condition:
#   - Returns None when self.first_event_time is None (no events have
#     been recorded yet)
#   - Otherwise returns the elapsed wall-clock duration between
#     self.first_event_time and the endpoint timestamp, expressed as a
#     possibly-fractional number of seconds
#   - The endpoint timestamp is self.last_event_time when
#     self.last_event_time is truthy; when self.last_event_time is
#     falsy (None or absent), the current UTC wall-clock instant is
#     used as the endpoint instead
# [SPEC]

# [INFO]
# datetime.now(timezone.utc) -> datetime
#   Pre-condition: none
#   Post-condition: Returns a timezone-aware datetime representing the
#     current instant in UTC
# [SPLIT]
# timedelta.total_seconds() -> float
#   Pre-condition: timedelta is a non-null duration
#   Post-condition: Returns the duration as a possibly-fractional
#     number of seconds
# [INFO]

    def elapsed(self):
        if self.first_event_time is None:
            return None
        end = self.last_event_time or datetime.now(timezone.utc)
        return (end - self.first_event_time).total_seconds()

# [SPEC]
# Unit: src/trace_writer-py/utc_now_iso.py
#
# utc_now_iso() -> str
#
# Pre-condition:
#   - none
#
# Post-condition:
#   - Returns the current UTC date and time formatted as an ISO 8601 string ending with "Z" as the UTC timezone designator
#   - The returned string includes microsecond precision
# [SPEC]

# [INFO]
# datetime.now(tz) -> datetime
#   Pre-condition: tz is a timezone-aware timezone object
#   Post-condition: returns a timezone-aware datetime object representing the current moment in the specified timezone
# [SPLIT]
# datetime.isoformat() -> str
#   Pre-condition: none
#   Post-condition: returns an ISO 8601 formatted string representation of the datetime including a UTC offset suffix
# [INFO]

def utc_now_iso():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

# [SPEC]
# Unit: fm_agent/extracted_functions/dashboard-py/_parse_iso.py
#
# _parse_iso(ts) -> Optional[datetime]
#
# Pre-condition:
#   - ts is a string or a falsy value (None, empty string).
#
# Post-condition:
#   - Returns None when ts is falsy.
#   - When ts is a non-empty string, attempts to interpret it as an
#     ISO 8601 timestamp.  A trailing "Z" (UTC designator) is accepted
#     and treated equivalently to "+00:00".
#   - On successful parse, returns a timezone-aware datetime object
#     whose components (year, month, day, hour, minute, second,
#     microsecond, UTC offset) match the values expressed in ts
#     according to ISO 8601 rules.
#   - Returns None when ts cannot be parsed as an ISO 8601 timestamp
#     (malformed format, invalid date/time values, etc.).
# [SPEC]

# [INFO]
# (no callees)
# [INFO]

def _parse_iso(ts):
    if not ts:
        return None
    if ts.endswith("Z"):
        ts = ts[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(ts)
    except Exception:
        return None

# [SPEC]
# Unit: fm_agent/extracted_functions/dashboard-py/_fmt_duration.py
#
# _fmt_duration(seconds) -> str
#
# Pre-condition:
#   - seconds is either None or a non-negative numeric value
#
# Post-condition:
#   - When seconds is None, returns the literal string "—" (U+2014 EM DASH)
#   - When seconds is not None, returns a string composed of up to three
#     space-separated segments ordered by decreasing time-unit magnitude
#     (hours, then minutes, then seconds), where each segment has the form
#     "<value><unit-suffix>" with unit-suffix in {"h", "m", "s"}:
#     * The hour segment ("<H>h") appears only when floor(seconds) >= 3600;
#       its value is the whole-hour count, never zero-padded
#     * The minute segment ("<M>m" or "<MM>m") appears when
#       floor(seconds) >= 60; its value is zero-padded to two digits only
#       when the hour segment is present, otherwise it is the bare
#       whole-minute count
#     * The second segment ("<S>s" or "<SS>s") always appears; its value is
#       zero-padded to two digits when any higher-magnitude segment is
#       present, otherwise it is the bare whole-second count
#   - All segment values (H, M, S) are derived from the integer part of
#     seconds (fractional seconds are truncated via floor)
# [SPEC]

# [INFO]
# (no callees)
# [INFO]

def _fmt_duration(seconds):
    if seconds is None:
        return "—"
    s = int(seconds)
    h, rem = divmod(s, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h}h {m:02d}m {s:02d}s"
    if m:
        return f"{m}m {s:02d}s"
    return f"{s}s"

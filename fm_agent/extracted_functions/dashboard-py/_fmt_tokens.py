# [SPEC]
# Unit: fm_agent/extracted_functions/dashboard-py/_fmt_tokens.py
#
# _fmt_tokens(n) -> str
#
# Pre-condition:
#   - n is either None or a non-negative numeric value.
#
# Post-condition:
#   - When n is None, returns "—" (U+2014 em dash).
#   - When n is a non-negative numeric value, returns a compact
#     human-readable string representation formatted as follows:
#       * n ≥ 1,000,000 → value divided by 10⁶, formatted to two
#         decimal places, suffixed with "M".
#       * 1,000 ≤ n < 1,000,000 → value divided by 10³, formatted
#         to one decimal place, suffixed with "K".
#       * n < 1,000 → decimal string representation of the integer
#         value of n, with no suffix.
#   - The returned string is minimal in length for its magnitude
#     category; the original value can be approximately recovered by
#     multiplying the numeric prefix by the magnitude implied by the
#     suffix (10³ for "K", 10⁶ for "M").
# [SPEC]

# [INFO]
# (no callees)
# [INFO]

def _fmt_tokens(n):
    if n is None:
        return "—"
    if n >= 1_000_000:
        return f"{n/1_000_000:.2f}M"
    if n >= 1_000:
        return f"{n/1_000:.1f}K"
    return str(n)

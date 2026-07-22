# [SPEC]
# Unit: fm_agent/extracted_functions/dashboard-py/_fmt_cost.py
#
# _fmt_cost(usd) -> str
#
# Pre-condition:
#   - usd is a non-negative numeric value (int or float) representing a
#     monetary amount in USD
#
# Post-condition:
#   - Returns a "$"-prefixed decimal string representing usd, rounded to
#     the nearest representable value
#   - The number of fractional digits in the returned string decreases
#     monotonically as usd increases: fractional-dollar amounts (below
#     one dollar) are formatted with the highest available precision
#     (three decimal places), while amounts at or above the thousands
#     threshold are formatted to the nearest whole dollar (zero decimal
#     places)
#   - The returned string is deterministic: the same numeric input always
#     produces the same string representation
# [SPEC]

# [INFO]
# (no callees)
# [INFO]

def _fmt_cost(usd):
    if usd is None:
        return "—"
    a = abs(usd)
    if a < 1:    return f"${usd:.3f}"
    if a < 100:  return f"${usd:.2f}"
    if a < 10000: return f"${usd:.1f}"
    return f"${usd:.0f}"

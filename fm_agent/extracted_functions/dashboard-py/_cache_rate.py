# [SPEC]
# Unit: fm_agent/extracted_functions/dashboard-py/_cache_rate.py
#
# _cache_rate(rows) -> tuple
#
# Pre-condition:
#   - rows is a sequence of (cache_read, total_input) pairs where
#     both cache_read and total_input are non-negative numeric values.
#
# Post-condition:
#   - Returns a 3-tuple (rate, cache_read_sum, input_sum).
#   - cache_read_sum is the sum of all cache_read values across rows.
#   - input_sum is the sum of all total_input values across rows.
#   - When input_sum > 0: rate is cache_read_sum / input_sum, a float
#     in the range [0.0, ∞) representing the fraction of total input
#     tokens served from cache.
#   - When input_sum == 0: rate is 0.0.
#   - The type of each sum is determined by the numeric types present
#     in rows (the result of adding the values in the sequence).
# [SPEC]

# [INFO]
# (no callees)
# [INFO]

def _cache_rate(rows):
    cr_total = sum(cr for cr, _ in rows)
    in_total = sum(t for _, t in rows)
    if in_total == 0:
        return None, cr_total, in_total
    return cr_total / in_total, cr_total, in_total

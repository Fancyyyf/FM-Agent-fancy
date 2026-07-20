# [SPEC]
# Unit: fm_agent/extracted_functions/dashboard-py/cache_hit_rate.py
#
# cache_hit_rate(self) -> Optional[float]
#
# Pre-condition:
#   - self.cache_window is an iterable of 2-tuples (a, b) where a and b are
#     numeric values.
#
# Post-condition:
#   - Returns None if self.cache_window is empty.
#   - Returns None if the sum of all second elements across self.cache_window
#     is zero.
#   - Otherwise, returns the result of (sum of all first elements) divided by
#     (sum of all second elements) as a float.
# [SPEC]

# [INFO]
# (no callees)
# [INFO]

    def cache_hit_rate(self):
        if not self.cache_window:
            return None
        cr_total = sum(cr for cr, _ in self.cache_window)
        in_total = sum(t for _, t in self.cache_window)
        if in_total == 0:
            return None
        return cr_total / in_total

    def cache_hit_rate(self):
        if not self.cache_window:
            return None
        cr_total = sum(cr for cr, _ in self.cache_window)
        in_total = sum(t for _, t in self.cache_window)
        if in_total == 0:
            return None
        return cr_total / in_total

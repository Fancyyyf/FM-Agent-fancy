def _cache_rate(rows):
    cr_total = sum(cr for cr, _ in rows)
    in_total = sum(t for _, t in rows)
    if in_total == 0:
        return None, cr_total, in_total
    return cr_total / in_total, cr_total, in_total

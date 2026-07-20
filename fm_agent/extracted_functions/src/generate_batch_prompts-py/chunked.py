# [SPEC]
# Unit: src/generate_batch_prompts-py/chunked.py
#
# chunked(items, size) -> list[list]
#
# Pre-condition:
#   - size is a positive integer
#   - items is a finite, ordered sequence (list)
#
# Post-condition:
#   - Returns a list of n sublists where n = ceil(len(items) / size)
#   - Each sublist has length ≤ size and all but possibly the last have length exactly size
#   - The concatenation of all sublists in returned order equals items in order
#   - No element of items belongs to more than one sublist
#   - The relative order of elements across the returned sublists matches their order in items
# [SPEC]

# [INFO]
# (no callees)
# [INFO]

def chunked(items: List[dict], size: int) -> List[List[dict]]:
    return [items[i : i + size] for i in range(0, len(items), size)]

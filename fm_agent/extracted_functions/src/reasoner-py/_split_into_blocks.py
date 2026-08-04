def _split_into_blocks(func):
    lines = func.strip().split('\n')
    total = len(lines)
    if total <= GRANULARITY:
        return [func.strip()]

    blocks = []
    i = 0
    while i < total:
        remaining = total - i
        if remaining <= GRANULARITY * 2:
            blocks.append('\n'.join(lines[i:]))
            break
        end = i + GRANULARITY
        blocks.append('\n'.join(lines[i:end]))
        i = end
    return blocks

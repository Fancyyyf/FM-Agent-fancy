def _split_into_blocks_braced(func, language):
    """
    Split function body into blocks respecting syntactic boundaries.
    """

    python_like = {"python"}

    if language.lower() in python_like:
        return _split_into_blocks(func)

    raw_lines = func.strip().split("\n")
    total = len(raw_lines)

    if total <= GRANULARITY:
        return [func.strip()]

    # normalize prefix
    stripped_lines = []
    for line in raw_lines:
        if line.startswith("Line "):
            colon = line.find(":", 5)
            if colon != -1:
                line = line[colon + 1:].lstrip()
        stripped_lines.append(line)

    # compute brace depth
    depths = _compute_brace_depth_per_line(stripped_lines)

    # define entry depth 
    entry_depth = depths[0] if total > 0 else 0

    if entry_depth == 0:
        entry_depth = next((d for d in depths if d > 0), 0)

    if entry_depth == 0:
        # fallback to safe splitter
        return _split_into_blocks(func)

    # greedy safe splitting
    blocks = []
    i = 0

    while i < total:
        remaining = total - i

        if remaining <= GRANULARITY * 2:
            blocks.append("\n".join(raw_lines[i:]))
            break

        target = i + GRANULARITY
        split_point = -1

        # ONLY split when we return to entry depth
        for j in range(target, total):
            if depths[j] == entry_depth:
                split_point = j
                break

        if split_point == -1:
            blocks.append("\n".join(raw_lines[i:]))
            break

        blocks.append("\n".join(raw_lines[i:split_point + 1]))
        i = split_point + 1

    return blocks

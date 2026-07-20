# [SPEC]
# Unit: src/reasoner-py/reasoner.py
#
# _split_into_blocks_braced(func, language) -> list[str]
#
# Pre-condition:
#   - func is a non-empty string containing the body of a function, each line optionally prefixed with "Line N: " followed by the source text
#   - language is a string identifying the source programming language
#
# Post-condition:
#   - Returns a non-empty list of strings, each being a contiguous, non-overlapping segment of the function body, appearing in the same order as in the original body
#   - For brace-delimited languages: every boundary between consecutive returned segments occurs at a line whose brace-nesting depth equals the brace-nesting depth at the first meaningful brace level of the function body. Each segment is therefore syntactically self-contained with respect to brace structure — it begins and ends at the same nesting depth as the function's entry depth
#   - For languages that use indentation for syntactic structure (classified as Python-like by the function): segments are split at boundaries that respect indentation-level changes, with each segment being a syntactically contiguous block
#   - The ordered concatenation of all returned strings, joined with newline characters, reconstructs the original function body text after stripping leading and trailing whitespace
# [SPEC]

# [INFO]
# _split_into_blocks(func) -> list[str]
#   Pre-condition: func is a non-empty string containing the body of a function
#   Post-condition: Returns a list of strings, each being a contiguous, non-overlapping segment of the function body split at indentation-level boundaries. The ordered concatenation of all returned strings joined with newline characters reconstructs the original function body text after stripping leading and trailing whitespace
# [SPLIT]
# _compute_brace_depth_per_line(stripped_lines) -> list[int]
#   Pre-condition: stripped_lines is a non-empty list of strings, each containing one line of function body text without "Line N:" prefixes
#   Post-condition: Returns a list of non-negative integers with length equal to stripped_lines. Each element at position i is the net brace count (opening braces '{' minus closing braces '}') accumulated from line 0 through line i inclusive, where braces appearing inside string literals and comments do not contribute to the count
# [INFO]

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

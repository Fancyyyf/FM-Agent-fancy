# [SPEC]
# Unit: src/reasoner-py/reasoner.py
#
# _split_into_blocks(func) -> list[str]
#
# Pre-condition:
#   - func is a non-empty string containing the body of a function
#   - GRANULARITY is a positive integer available in the enclosing scope
#
# Post-condition:
#   - Returns a non-empty list of strings, each being a contiguous, non-overlapping segment of the function body, appearing in the same order as in the original body
#   - When the line count of func does not exceed GRANULARITY, returns a single-element list containing the function body with leading and trailing whitespace removed
#   - When the line count of func exceeds GRANULARITY, every segment except the last contains exactly GRANULARITY lines
#   - The last segment contains between 1 and 2 × GRANULARITY lines inclusive
#   - Each line within a segment preserves its original content, including indentation whitespace
#   - The ordered concatenation of all returned strings, joined with newline characters, reconstructs the original function body text after stripping leading and trailing whitespace
# [SPEC]

# [INFO]
# (no callees)
# [INFO]

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

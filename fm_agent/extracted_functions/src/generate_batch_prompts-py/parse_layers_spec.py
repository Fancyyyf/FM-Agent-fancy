# [SPEC]
# Unit: src/generate_batch_prompts-py/parse_layers_spec.py
#
# parse_layers_spec(layers_spec: str) -> (int, int)
#
# Pre-condition:
#   - layers_spec is a string in the format "N" or "N-M" where N and M are
#     non-negative integers, after stripping leading/trailing whitespace
#
# Post-condition:
#   - Returns an inclusive (start, end) pair of integer layer indices
#   - When layers_spec contains no "-" character: returns (N, N) where N is the
#     integer value of the entire string
#   - When layers_spec contains a "-" character: splits on the first "-", parses
#     the left part as start and right part as end, returns (start, end)
#   - Raises ValueError if start > end, with a message indicating the range is invalid
#   - Raises ValueError if the string is not parseable as "N" or "N-M" with valid
#     integer components
# [SPEC]

# [INFO]
# (no callees)
# [INFO]

def parse_layers_spec(layers_spec: str) -> Tuple[int, int]:
    text = layers_spec.strip()
    if "-" not in text:
        idx = int(text)
        return idx, idx
    left, right = text.split("-", 1)
    start = int(left.strip())
    end = int(right.strip())
    if start > end:
        raise ValueError("invalid --layers range: start > end")
    return start, end

# [SPEC]
# Unit: src/llm_client.py
#
# _inject_targets() -> list[str]
#
# Pre-condition:
#   - None (no arguments required)
#
# Post-condition:
#   - Returns a list of non-empty strings representing the configured targets for
#     user-id metadata injection into request bodies
#   - The returned values are determined by the INJECT_HOST environment variable:
#     when set, the value is parsed as a comma-separated list, each segment is
#     stripped of leading and trailing whitespace, and any resulting empty segments
#     are discarded
#   - When INJECT_HOST is unset or empty, returns an empty list
#   - The relative order of elements in the returned list matches the order of
#     their corresponding segments in INJECT_HOST
# [SPEC]

# [INFO]
# (no callees)
# [INFO]

def _inject_targets():
    return [s.strip() for s in (os.environ.get("INJECT_HOST") or "").split(",") if s.strip()]

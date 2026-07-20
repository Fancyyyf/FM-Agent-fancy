# [SPEC]
# Unit: src/languages/erlang-py/_fingerprint_digest.py
#
# _fingerprint_digest(fingerprint: tuple) -> str
#
# Pre-condition:
#   - fingerprint is a tuple whose elements are all JSON-serializable
#     (each element is one of: str, int, float, bool, None, list, dict, or
#     tuple — any value that json.dumps can serialize without raising
#     TypeError)
#
# Post-condition:
#   - Returns a 64-character lowercase hexadecimal string (SHA-256 digest)
#   - The result is deterministic: for any two tuples t1 and t2,
#     t1 == t2 implies _fingerprint_digest(t1) == _fingerprint_digest(t2)
#   - Two tuples that are not equal produce different digests with
#     overwhelming probability (consistent with SHA-256 collision resistance)
#   - The digest is computed from a compact JSON serialization of the tuple
#     (no indentation, no whitespace between keys/values, and Unicode
#     characters preserved without ASCII escaping)
# [SPEC]

# [INFO]
# (no callees)
# [INFO]

def _fingerprint_digest(fingerprint: tuple) -> str:
    payload = json.dumps(fingerprint, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()

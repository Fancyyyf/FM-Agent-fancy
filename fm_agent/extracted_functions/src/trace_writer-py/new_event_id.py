# [SPEC]
# Unit: src/trace_writer-py/new_event_id.py
#
# new_event_id(prefix) -> str
#
# Pre-condition:
#   - prefix is a non-empty string
#
# Post-condition:
#   - Returns a string composed of prefix, a single underscore, and a 32-character lowercase hexadecimal string
#   - The returned identifier is globally unique: it differs from every identifier previously returned by any invocation of new_event_id
# [SPEC]

# [INFO]
# uuid.uuid4() -> UUID
#   Pre-condition: none
#   Post-condition: returns a randomly generated RFC 4122 version 4 UUID
# [SPLIT]
# UUID.hex -> str
#   Pre-condition: none
#   Post-condition: returns the UUID as a 32-character lowercase hexadecimal string without hyphens or other separators
# [INFO]

def new_event_id(prefix="evt"):
    return f"{prefix}_{uuid.uuid4().hex}"

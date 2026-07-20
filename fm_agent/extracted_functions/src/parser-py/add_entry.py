# [SPEC]
# Unit: src/parser-py/add_entry.py
#
# add_entry(self, function_name: str, signature: str, spec: str) -> None
#
# Pre-condition:
#   - function_name is a non-empty string
#   - signature is a string
#   - spec is a string (may be empty)
#
# Post-condition:
#   - The value stored for key function_name in the map equals the spec argument
#   - The value stored for key function_name in self.signatures equals the signature argument
# [SPEC]

# [INFO]
# (no callees)
# [INFO]

    def add_entry(self, function_name, signature, spec):
        self[function_name] = spec
        self.signatures[function_name] = signature

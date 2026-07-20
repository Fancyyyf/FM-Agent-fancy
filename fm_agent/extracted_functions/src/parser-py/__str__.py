# [SPEC]
# Unit: src/parser-py/__str__.py
#
# FunctionSpecMap.__str__(self) -> str
#
# Pre-condition:
#   - self is a mapping from function names (str) to spec text (str or falsy)
#   - self.signatures is a dict mapping function names (str) to signature line strings (str)
#
# Post-condition:
#   - Returns a single string representing every entry in self
#   - Each function_name in self produces exactly one entry in the output
#   - For each function_name, the entry's signature portion is self.signatures[function_name]
#     when that key exists; otherwise it is the function_name itself
#   - When the corresponding spec value is truthy (non-empty, non-None), the entry has the
#     form "{signature}\n{spec}"; when the spec value is falsy (empty string or None), the
#     entry consists of the signature alone
#   - Entries appear in the iteration order of self
#   - Entries are separated by "\n\n" (a single blank line), with no trailing separator
# [SPEC]

# [INFO]
# (no callees)
# [INFO]

    def __str__(self):
        formatted_entries = []
        for function_name, spec in self.items():
            signature = self.signatures.get(function_name, function_name)
            if spec:
                formatted_entries.append(f"{signature}\n{spec}")
            else:
                formatted_entries.append(signature)
        return "\n\n".join(formatted_entries)

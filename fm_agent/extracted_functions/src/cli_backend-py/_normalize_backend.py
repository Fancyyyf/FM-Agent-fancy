# [SPEC]
# Unit: src/cli_backend.py
#
# _normalize_backend(value) -> str
#
# Pre-condition:
#   - value is either None, a string, or any value whose string representation
#     (after stripping leading and trailing whitespace and lowercasing)
#     produces an empty string, a recognized sentinel, the literal "auto",
#     a recognized alias, or an unrecognized string
#
# Post-condition:
#   - When value is None, or when its normalized form is the empty string,
#     or when the normalized form is one of the recognized disable-sentinel
#     strings ("0", "false", "no", "off"): returns "opencode", the canonical
#     name of the default backend
#   - When the normalized form equals "auto": returns "auto" unchanged,
#     deferring resolution of the auto-sentinel to the caller
#   - When the normalized form matches a recognized backend alias:
#     returns the canonical backend name that the alias maps to
#     (aliases map to the set {"opencode", "codex-cli", "claude-cli"})
#   - When the normalized form matches none of the above categories:
#     returns the normalized form itself unchanged as a pass-through
#   - The returned string is always non-empty, case-normalized to lowercase,
#     and drawn from the set {"opencode", "codex-cli", "claude-cli", "auto"}
#     unioned with the domain of unrecognized pass-through strings
#   - The same input value always produces the same output (pure function)
#   - Returns a str in all cases — no exceptions are raised for any input
# [SPEC]

# [INFO]
# (no callees)
# [INFO]

def _normalize_backend(value):
    backend = (value or "").strip().lower()
    if not backend or backend in {"0", "false", "no", "off"}:
        return "opencode"
    if backend == "auto":
        return "auto"
    return _BACKEND_ALIASES.get(backend, backend)

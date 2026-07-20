# [SPEC]
# Unit: src/languages/codegraph-py/_fqn_for.py
#
# _fqn_for(file_path: str, name: str) -> str
#
# Pre-condition:
#   - file_path is a string representing a filesystem path to a source file
#   - name is a non-empty canonicalized function name string (template
#     parameters stripped, operator names normalized to safe identifiers)
#
# Post-condition:
#   - Returns a fully-qualified function name (FQN) string whose components
#     are separated by "::"
#   - The FQN consists of, in order: the non-empty directory components of
#     file_path (excluding the source filename), a single file-derived
#     component, and name
#   - The file-derived component is obtained from the filename portion of
#     file_path: if the filename contains at least one "." after a non-empty
#     prefix, the last "." is replaced by "-"; otherwise the filename is
#     used unchanged
#   - Directory components are extracted independently of OS path separator
#     convention and empty components (from leading or consecutive
#     separators) are excluded
#   - The returned FQN is deterministic and identical to the FQN that the
#     call-graph builder computes for the extracted function file
#     corresponding to the same (file_path, name) pair
# [SPEC]

# [INFO]
# (no callees)
# [INFO]

def _fqn_for(file_path: str, name: str) -> str:
    """Build the FQN of a function, identical to generate_topdown_layers._file_to_fqn.

    The extracted layout for a source file ``<dir>/<base>.<ext>`` is
    ``<dir>/<base>-<ext>/<name>.<ext>``, whose FQN is ``dir::base-ext::name``.
    Constructing the same string here lets get_call_edges emit edges keyed by the
    exact same FQN the call-graph builder assigns to each extracted function, so
    codegraph's precisely-resolved caller/callee node identity is preserved
    instead of being collapsed to a bare name.
    """
    norm = file_path.replace(os.sep, "/")
    d = os.path.dirname(norm)
    base = os.path.basename(norm)
    last_dot = base.rfind(".")
    dashed = base[:last_dot] + "-" + base[last_dot + 1:] if last_dot > 0 else base
    parts = [p for p in d.split("/") if p]
    parts += [dashed, name]
    return "::".join(parts)

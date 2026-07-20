# [SPEC]
# Unit: src/pipeline_setup-py/_merge_descriptions.py
#
# _merge_descriptions(target_desc, source_desc) -> str
#
# Pre-condition:
#   - target_desc is a string
#   - source_desc is a string
#
# Post-condition:
#   - Returns target_desc unchanged when source_desc, after stripping leading
#     and trailing whitespace, is empty
#   - Returns target_desc unchanged when the stripped source_desc is a substring
#     of target_desc
#   - Returns source_desc unchanged when target_desc is empty and stripped
#     source_desc is non-empty and is not a substring of target_desc
#   - Otherwise, returns target_desc joined with source_desc using a single
#     space separator
# [SPEC]

# [INFO]
# (no callees)
# [INFO]

def _merge_descriptions(target_desc, source_desc):
    """Append a removed module's description to the owning module's description.

    Avoids re-merging the same content if it is already present.
    """
    source_desc = (source_desc or "").strip()
    if not source_desc:
        return target_desc
    if source_desc in target_desc:
        return target_desc
    if not target_desc:
        return source_desc
    return f"{target_desc}\n\n{source_desc}"

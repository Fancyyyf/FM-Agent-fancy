# [SPEC]
# Unit: src/generate_batch_prompts-py/extract_callee_spec_from_info.py
#
# extract_callee_spec_from_info(info_block, callee_fqn, aliases) -> Optional[str]
#
# Pre-condition:
#   - info_block is a string containing zero or more callee entries, where each entry is a block of lines delimited by "[SPLIT]" markers; each entry begins with a signature line followed by Pre-condition and Post-condition lines
#   - callee_fqn is a non-empty string representing a fully qualified function name
#   - aliases is None or a sequence of alternative name strings for the same callee
#
# Post-condition:
#   - If info_block contains a [SPLIT]-delimited entry whose first line mentions callee_fqn or any of the aliases (when compared with the comment prefix stripped from that line), returns the full text of that entry exactly as it appears in info_block; otherwise returns None
#   - Entries whose content includes the literal string "(no callees)" are treated as non-matching regardless of other content
#   - The comment prefix used for stripping is the text preceding a "[SPLIT]" marker within info_block itself, or the first whitespace-delimited token of the block's first non-empty line if no "[SPLIT]" marker is present
#   - Within the first line of a candidate entry, the mention check succeeds if any of the search names (callee_fqn or alias) appears as a substring or token
#   - The returned entry text preserves the original formatting and comment prefix as found in info_block
# [SPEC]

# [INFO]
# (no callees)
# [INFO]

def extract_callee_spec_from_info(
    info_block: str,
    callee_fqn: str,
    aliases: Optional[Sequence[str]] = None,
) -> Optional[str]:
    """Find the [SPLIT]-separated entry for callee_fqn in an info_block."""
    # Detect comment prefix from the info_block content itself
    prefix = ""
    for line in info_block.splitlines():
        stripped = line.strip()
        if stripped:
            idx = stripped.find("[SPLIT]")
            if idx != -1:
                prefix = stripped[:idx].rstrip()
                break
    # If no [SPLIT] found in block, infer prefix from first non-empty line
    if not prefix:
        for line in info_block.splitlines():
            stripped = line.strip()
            if stripped:
                m = re.match(r'^(\S+)\s', stripped)
                if m:
                    prefix = m.group(1)
                break

    split_tag = f"{prefix} [SPLIT]" if prefix else "[SPLIT]"
    names = _callee_match_names(callee_fqn, aliases or ())
    for entry in info_block.split(split_tag):
        entry = entry.strip()
        if not entry or "(no callees)" in entry:
            continue
        first_line = entry.split("\n")[0].strip()
        # Strip the comment prefix to get the actual content
        if prefix and first_line.startswith(prefix):
            first_line = first_line[len(prefix):].strip()
        if any(_info_line_mentions_name(first_line, name) for name in names):
            return entry
    return None

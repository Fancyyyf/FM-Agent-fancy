# [SPEC]
# Unit: src/domain_knowledge.py
#
# collect_domain_knowledge_paths(cli_paths, base_dir, fallback_base_dir) -> list[str]
#
# Pre-condition:
#   - cli_paths is None or an iterable of path-like strings (potentially nested)
#   - base_dir is a string referencing an existing directory
#   - fallback_base_dir is None or a string referencing an existing directory
#
# Post-condition:
#   - Returns a list of resolved absolute file path strings, one per distinct domain-knowledge markdown file
#   - The returned list includes paths sourced from two origins: the FM_AGENT_DOMAIN_KNOWLEDGE environment variable (split on os.pathsep) and the flattened cli_paths
#   - An empty or unset FM_AGENT_DOMAIN_KNOWLEDGE environment variable contributes no paths
#   - cli_paths entries that are None or empty contribute no paths
#   - Each path in the returned list is absolute; if a source path is relative, it is resolved against base_dir, and if that resolution does not yield an existing file, it is resolved against fallback_base_dir as a secondary base
#   - The returned list contains no duplicate entries
#   - The returned list is empty if no valid domain-knowledge paths are found
# [SPEC]

# [INFO]
# _split_env_paths(env_value) -> list[str]
#   Pre-condition: env_value is None or a string
#   Post-condition: if env_value is a non-empty string, splits it on os.pathsep and returns the resulting list of path strings; if env_value is None or empty, returns an empty list
# [SPLIT]
# _flatten_paths(cli_paths) -> list[str]
#   Pre-condition: cli_paths is None or an iterable that may contain nested iterables or individual path strings
#   Post-condition: returns a flat list of path strings with all nesting removed; None and empty values are excluded
# [SPLIT]
# resolve_domain_knowledge_paths(paths, base_dir, fallback_base_dir) -> list[str]
#   Pre-condition: paths is a list of path strings; base_dir and fallback_base_dir are directory paths
#   Post-condition: returns a list of absolute file paths, with each relative path resolved first against base_dir then fallback_base_dir; only paths that resolve to existing files are included; duplicates are removed
# [INFO]

def collect_domain_knowledge_paths(cli_paths, base_dir, fallback_base_dir=None):
    """Collect markdown paths from CLI values plus FM_AGENT_DOMAIN_KNOWLEDGE."""
    paths = []
    paths.extend(_split_env_paths(os.environ.get("FM_AGENT_DOMAIN_KNOWLEDGE")))
    paths.extend(_flatten_paths(cli_paths))
    return resolve_domain_knowledge_paths(
        paths,
        base_dir=base_dir,
        fallback_base_dir=fallback_base_dir,
    )

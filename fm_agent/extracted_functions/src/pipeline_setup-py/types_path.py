# [SPEC]
# Unit: src/pipeline_setup.py
#
# types_path(num) -> str
#
# Pre-condition:
#   - num is an integer representing a phase number
#   - domain_dir is defined in the enclosing scope as a valid directory path string pointing
#     to the domain context directory within the fm_agent workspace
#
# Post-condition:
#   - Returns the absolute file path to the domain context types file for phase num,
#     constructed as <domain_dir>/phase_<num:02d>_types.txt where num is zero-padded to
#     at least 2 digits
#   - The returned path uses the operating system's native path separator
#   - The return value is purely a path string — no filesystem side effects occur
# [SPEC]

# [INFO]
# (no callees)
# [INFO]

    def types_path(num):
        return os.path.join(domain_dir, f"phase_{num:02d}_types.txt")

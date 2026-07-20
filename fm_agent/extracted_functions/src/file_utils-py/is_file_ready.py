# [SPEC]
# Unit: src/file_utils.py
#
# is_file_ready(file_path) -> bool
#
# Pre-condition:
#   - file_path is a string
#
# Post-condition:
#   - Returns True if and only if file_path references a file that exists, is readable as text, and contains at least two lines that include the substring '[SPEC]' and at least two lines that include the substring '[INFO]'
#   - Returns False if file_path does not reference an existing readable file, or if the file content cannot be decoded as Unicode text, or if the file lacks the minimum required specification markers (fewer than two lines containing '[SPEC]' or fewer than two lines containing '[INFO]')
# [SPEC]

# [INFO]
# (no callees)
# [INFO]

def is_file_ready(file_path):
    """Check if a file has [SPEC] ... [SPEC] and [INFO] ... [INFO] headers."""
    try:
        with open(file_path, 'r') as f:
            content = f.read()
    except (OSError, UnicodeDecodeError):
        return False

    lines = content.splitlines()
    spec_count = 0
    info_count = 0

    for line in lines:
        if '[SPEC]' in line:
            spec_count += 1
        if '[INFO]' in line:
            info_count += 1

    return spec_count >= 2 and info_count >= 2

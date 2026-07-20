# [SPEC]
# Unit: src/reasoner-py/_parse_spec_conditions.py
#
# _parse_spec_conditions(spec) -> (str | None, str | None)
#
# Pre-condition:
#   - spec is a string that may contain specification text with Pre-condition and/or
#     Post-condition sections
#
# Post-condition:
#   - Returns a 2-tuple (pre_condition, post_condition)
#   - pre_condition is the text content between the "Pre-condition:" header line and the
#     next section boundary, with leading and trailing whitespace stripped;
#     it is None when no "Pre-condition:" section is found in the spec string
#   - post_condition is the text content between the "Post-condition:" header line and
#     the end of the string, with leading and trailing whitespace stripped;
#     it is None when no "Post-condition:" section is found in the spec string
# [SPEC]

# [INFO]
# (no callees)
# [INFO]

def _parse_spec_conditions(spec):
    pre_match = re.search(r'Pre-condition:\s*\n(.*?)(?=\nPost-condition:|\Z)', spec, re.DOTALL)
    post_match = re.search(r'Post-condition:\s*\n(.*)', spec, re.DOTALL)
    pre = pre_match.group(1).strip() if pre_match else None
    post = post_match.group(1).strip() if post_match else None
    return pre, post

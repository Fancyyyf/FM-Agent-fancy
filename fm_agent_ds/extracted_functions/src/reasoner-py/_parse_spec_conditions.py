def _parse_spec_conditions(spec):
    pre_match = re.search(r'Pre-condition:\s*\n(.*?)(?=\nPost-condition:|\Z)', spec, re.DOTALL)
    post_match = re.search(r'Post-condition:\s*\n(.*)', spec, re.DOTALL)
    pre = pre_match.group(1).strip() if pre_match else None
    post = post_match.group(1).strip() if post_match else None
    return pre, post

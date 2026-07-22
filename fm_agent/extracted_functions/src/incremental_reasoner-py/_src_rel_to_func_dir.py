# [SPEC]
# Unit: fm_agent/extracted_functions/src/incremental_reasoner-py/_src_rel_to_func_dir.py
#
# _src_rel_to_func_dir(proj_dir, abs_src) -> (str, str)
#
# Pre-condition:
#   - proj_dir is an absolute directory path
#   - abs_src is an absolute file path within proj_dir
#
# Post-condition:
#   - Returns a tuple (func_dir, ext) where both components are strings
#   - func_dir is an absolute directory path formed by:
#     1. Stripping the proj_dir prefix from abs_src to obtain a relative path
#     2. Partitioning the relative path into directory components and a basename
#     3. Replacing the last (rightmost) dot in the basename with a hyphen to
#        produce a terminal directory name; when the basename contains no dot
#        at a position after its first character, the terminal directory name
#        equals the basename unchanged
#     4. Concatenating proj_dir/fm_agent/extracted_functions, the directory
#        components of the relative path, and the terminal directory name
#   - ext is the substring of the source basename following the last (rightmost)
#     dot when that dot occurs after the first character of the basename;
#     otherwise ext is the empty string
#   - The two return values depend only on the string content of the arguments;
#     they do not depend on filesystem state such as whether either path exists
#     on disk
# [SPEC]

def _src_rel_to_func_dir(proj_dir, abs_src):
    """(func_dir, ext) for a source file: the extracted-functions directory that
    holds its functions (``.../loader-cpp``) and the source extension."""
    extracted_base = os.path.join(proj_dir, "fm_agent", "extracted_functions")
    rel = os.path.relpath(abs_src, proj_dir)
    src_dir = os.path.dirname(rel)
    src_base = os.path.basename(rel)
    last_dot = src_base.rfind(".")
    if last_dot > 0:
        dir_name = src_base[:last_dot] + "-" + src_base[last_dot + 1:]
        ext = src_base[last_dot + 1:]
    else:
        dir_name = src_base
        ext = ""
    func_dir = os.path.join(extracted_base, src_dir, dir_name) if src_dir else os.path.join(extracted_base, dir_name)
    return func_dir, ext

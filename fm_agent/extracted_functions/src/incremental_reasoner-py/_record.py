# [SPEC]
# Unit: fm_agent/extracted_functions/src/incremental_reasoner-py/_record.py
#
# _record(rel_path, score) -> None
#
# Pre-condition:
#   - scored is a mutable mapping accessible in the enclosing scope, mapping string keys
#     to numeric values
#   - rel_path is a string key
#   - score is a numeric value comparable with > against values stored in scored
#
# Post-condition:
#   - scored[rel_path] equals max(score, previous_value) where previous_value is the
#     value associated with rel_path before the call, or a value strictly less than
#     any possible score if rel_path was absent
#   - When rel_path was already present in scored with a value ≥ score, scored is
#     unchanged
# [SPEC]

# [INFO]
# (no callees)
# [INFO]

    def _record(rel_path, score):
        if rel_path not in scored or score > scored[rel_path]:
            scored[rel_path] = score

# [SPEC]
# Unit: src/incremental_reasoner-py/_order_key.py
#
# _order_key(fqn) -> Tuple[int, str]
#
# Pre-condition:
#   - fqn is a string representing a fully-qualified function name
#   - order_index is a dict mapping some FQN strings to non-negative integer indices
#
# Post-condition:
#   - Returns a two-element tuple (position, fqn) suitable as a sort key for top-down topological ordering
#   - When fqn is a key in order_index, position equals the integer value associated with fqn in order_index
#   - When fqn is not a key in order_index, position equals the number of entries in order_index
#   - For any two FQNs a, b both present in order_index: a sorts before b iff order_index[a] < order_index[b]
#   - Any FQN not present in order_index sorts after all FQNs that are present in order_index
# [SPEC]

# [INFO]
# (no callees)
# [INFO]

    def _order_key(fqn):
        return (order_index.get(fqn, len(order_index)), fqn)

    def _order_key(fqn):
        return (order_index.get(fqn, len(order_index)), fqn)

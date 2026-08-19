    def add_entry(self, function_name, signature, spec):
        self[function_name] = spec
        self.signatures[function_name] = signature

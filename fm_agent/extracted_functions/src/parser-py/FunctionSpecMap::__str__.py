    def __str__(self):
        formatted_entries = []
        for function_name, spec in self.items():
            signature = self.signatures.get(function_name, function_name)
            if spec:
                formatted_entries.append(f"{signature}\n{spec}")
            else:
                formatted_entries.append(signature)
        return "\n\n".join(formatted_entries)

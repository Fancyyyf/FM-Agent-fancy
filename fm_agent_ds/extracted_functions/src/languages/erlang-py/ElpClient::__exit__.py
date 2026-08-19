    def __exit__(self, exc_type, exc, tb):
        self.close()
        return False

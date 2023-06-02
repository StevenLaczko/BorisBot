class ContextLimitException(Exception):
    def __init__(self, message="Context length limit exceeded."):
        self.message = message
        super().__init__(self.message)


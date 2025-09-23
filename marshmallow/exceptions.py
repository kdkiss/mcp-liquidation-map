class ValidationError(Exception):
    """Replicates the core behaviour of marshmallow.ValidationError."""

    def __init__(self, messages):
        if messages is None:
            messages = {}
        self.messages = messages
        super().__init__(str(messages))

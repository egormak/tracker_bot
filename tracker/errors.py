
class InvalidStatusCode(Exception):
    "Raised when status is not 200"
    def __init__(self, message):
        self.message = message
        super().__init__(self.message)
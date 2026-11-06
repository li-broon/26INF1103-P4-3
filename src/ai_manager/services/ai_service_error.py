# Raised by an AIService when the AI Cannot be Reached or Replies with Error
class AIServiceError(Exception):
    def __init__(self, message: str, code: int | None = None, status: str | None = None):
        super().__init__(message)
        self.message = message
        self.code = code
        self.status = status
class AppException(Exception):
    """
    Base application exception.
    All custom exceptions should inherit from this class.
    """

    status_code: int = 500
    message: str = "Application error"

    def __init__(self, message: str | None = None):
        if message:
            self.message = message
        super().__init__(self.message)

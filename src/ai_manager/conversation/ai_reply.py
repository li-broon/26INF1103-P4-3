# What the Conversation Returns to 'io_manager' after Each Worker Message
# (On Failure, 'error' Holds the Message; error_code/error_status are Set for API Errors)
class AIReply:
    def __init__(self, reply: str = "", is_complete: bool = False, report: dict | None = None,
                 error: str | None = None, error_code: int | None = None, error_status: str | None = None):
        self.reply = reply
        self.is_complete = is_complete
        self.report = report if report is not None else {}
        self.error = error
        self.error_code = error_code
        self.error_status = error_status

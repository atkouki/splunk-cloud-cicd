class CicdError(Exception):
    exit_code = 1


class PackagingError(CicdError):
    exit_code = 2


class InspectError(CicdError):
    exit_code = 3


class AcsError(CicdError):
    exit_code = 4

    def __init__(self, message, status=None, body=None):
        super().__init__(message)
        self.status = status
        self.body = body


class VerifyError(CicdError):
    exit_code = 5

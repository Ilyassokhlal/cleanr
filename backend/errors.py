

class CleanrError(Exception):
    """Something the user can act on. Carries the status to return."""

    status_code = 400


class FileTooLarge(CleanrError):
    """The user tries to upload a file that exceeds the maximum size."""
    status_code = 413


class ProcessingFailed(CleanrError):
    """The backend fails to process the file for some reason."""
    status_code = 422
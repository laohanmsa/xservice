"""Provider-specific exceptions."""


class ProviderError(Exception):
    """Base exception for provider-related errors."""


class SessionAcquisitionError(ProviderError):
    """Raised when a session cannot be acquired."""


class OperationError(ProviderError):
    """Raised when a provider operation fails."""

    def __init__(self, message: str, underlying_error: Exception = None):
        super().__init__(message)
        self.underlying_error = underlying_error

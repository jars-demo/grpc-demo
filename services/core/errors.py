"""Domain errors. Each interface maps them to its own status codes (gRPC status / HTTP status)."""


class DomainError(Exception):
    """Base class for errors the caller can fix."""


class InvalidArgument(DomainError):
    """The request is malformed. gRPC: INVALID_ARGUMENT. HTTP: 422."""


class NotFound(DomainError):
    """The requested item does not exist. gRPC: NOT_FOUND. HTTP: 404."""

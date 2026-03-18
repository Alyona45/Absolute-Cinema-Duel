class ServiceError(Exception):
    """Base class for service-layer errors."""


class SessionNotFoundError(ServiceError):
    pass


class AccessDeniedError(ServiceError):
    pass


class AlreadyParticipantError(ServiceError):
    pass


class ParticipantNotFoundError(ServiceError):
    pass


class SessionMovieNotFoundError(ServiceError):
    pass


class InvalidOperationError(ServiceError):
    pass

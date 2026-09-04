"""Application errors carry a stable machine-readable code; the API layer maps codes to HTTP."""

from __future__ import annotations


class AppError(Exception):
    """Base class for every error a use case can raise."""

    code: str = "app_error"
    default_message: str = "The request could not be completed."

    def __init__(self, message: str | None = None, *, fields: dict[str, str] | None = None) -> None:
        self.message = message or self.default_message
        self.fields = fields
        super().__init__(self.message)


class InvalidCredentials(AppError):
    code = "invalid_credentials"
    default_message = "Incorrect email or password, or the account is locked or not yet active."


class InvalidRefreshToken(AppError):
    code = "invalid_refresh"
    default_message = "The session could not be refreshed. Please sign in again."


class Unauthenticated(AppError):
    code = "unauthenticated"
    default_message = "Authentication is required."


class Forbidden(AppError):
    code = "forbidden"
    default_message = "You do not have permission to do that."


class InvalidToken(AppError):
    code = "invalid_token"
    default_message = "The link is invalid, has expired or has already been used."


class WeakPassword(AppError):
    code = "weak_password"
    default_message = "The password does not meet the policy."

    def __init__(self, reason: str) -> None:
        super().__init__(fields={"new_password": reason})


class RateLimited(AppError):
    code = "rate_limited"
    default_message = "Too many requests. Please wait and try again."

    def __init__(self, retry_after: int) -> None:
        self.retry_after = max(1, retry_after)
        super().__init__()


class NotFound(AppError):
    code = "not_found"
    default_message = "The requested item does not exist."


class AlreadyDecided(AppError):
    code = "already_decided"
    default_message = "This account request has already been decided."


class EmailTaken(AppError):
    code = "email_taken"
    default_message = "A user with this email address already exists."


class SelfModification(AppError):
    code = "self_modification"
    default_message = "You cannot change your own role or active status."


class UserInactive(AppError):
    code = "user_inactive"
    default_message = "The account is deactivated. Reactivate it before issuing a link."

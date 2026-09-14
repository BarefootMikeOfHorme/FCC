"""Deterministic application and readiness errors."""

from __future__ import annotations

from collections.abc import Iterable
from free_claude_code.core.failures import FailureKind


class ApplicationError(Exception):
    """Base class for deterministic request/readiness failures."""

    kind: FailureKind
    status_code: int

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class InvalidRequestError(ApplicationError):
    """The accepted request cannot be executed deterministically."""

    kind = FailureKind.INVALID_REQUEST
    status_code = 400


class UnknownProviderError(InvalidRequestError):
    """Raised when a provider name is not recognized."""

    @classmethod
    def for_provider(
        cls,
        provider_id: str,
        supported_provider_ids: Iterable[str],
    ) -> UnknownProviderError:
        supported = "', '".join(supported_provider_ids)
        return cls(
            f"Unknown provider_type: '{provider_id}'. Supported: '{supported}'"
        )


class ApplicationUnavailableError(ApplicationError):
    """The application cannot currently provide a request runtime."""

    kind = FailureKind.UNAVAILABLE
    status_code = 503

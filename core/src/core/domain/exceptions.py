from __future__ import annotations

from typing import Any
from uuid import UUID


class DomainError(Exception):
    """Base for all domain errors. Class name serves as error code."""

    def __init__(self, message: str, **context: Any) -> None:
        super().__init__(message)
        self.message = message
        self.context = context


class EntityNotFoundError(DomainError):
    """Raised when an entity cannot be found by its identifier."""

    def __init__(self, entity_type: str, entity_id: UUID) -> None:
        super().__init__(
            f"{entity_type} with id {entity_id} not found",
            entity_type=entity_type,
            entity_id=entity_id,
        )


class InvalidEntityStateError(DomainError):
    """Raised when an entity operation is invalid for its current state."""

    def __init__(self, entity_type: str, entity_id: Any, reason: str) -> None:
        super().__init__(
            f"{entity_type} {entity_id} is in invalid state: {reason}",
            entity_type=entity_type,
            entity_id=entity_id,
            reason=reason,
        )


class DuplicateEntityError(DomainError):
    """Raised when attempting to create an entity that already exists."""

    def __init__(self, entity_type: str, identifier: str) -> None:
        super().__init__(
            f"{entity_type} with identifier {identifier} already exists",
            entity_type=entity_type,
            identifier=identifier,
        )


class ValidationError(DomainError):
    """Raised when domain validation fails on an entity field."""

    def __init__(self, entity_type: str, field: str, reason: str) -> None:
        super().__init__(
            f"Validation failed on {entity_type}.{field}: {reason}",
            entity_type=entity_type,
            field=field,
            reason=reason,
        )

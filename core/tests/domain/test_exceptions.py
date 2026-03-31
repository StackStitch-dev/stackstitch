from __future__ import annotations

from uuid import uuid4

from core.domain.exceptions import (
    DomainError,
    DuplicateEntityError,
    EntityNotFoundError,
    InvalidEntityStateError,
    ValidationError,
)


class TestDomainError:
    def test_stores_message_and_context(self) -> None:
        err = DomainError("something failed", key="value", count=42)
        assert err.message == "something failed"
        assert err.context == {"key": "value", "count": 42}
        assert str(err) == "something failed"

    def test_empty_context(self) -> None:
        err = DomainError("plain error")
        assert err.context == {}


class TestEntityNotFoundError:
    def test_stores_entity_type_and_id(self) -> None:
        eid = uuid4()
        err = EntityNotFoundError("Investigation", eid)
        assert err.context["entity_type"] == "Investigation"
        assert err.context["entity_id"] == eid
        assert "Investigation" in err.message
        assert str(eid) in err.message

    def test_is_domain_error(self) -> None:
        err = EntityNotFoundError("Stream", uuid4())
        assert isinstance(err, DomainError)


class TestInvalidEntityStateError:
    def test_stores_context_fields(self) -> None:
        eid = uuid4()
        err = InvalidEntityStateError("Investigation", eid, "must be PENDING to start")
        assert err.context["entity_type"] == "Investigation"
        assert err.context["entity_id"] == eid
        assert err.context["reason"] == "must be PENDING to start"

    def test_is_domain_error(self) -> None:
        err = InvalidEntityStateError("Invocation", uuid4(), "reason")
        assert isinstance(err, DomainError)


class TestDuplicateEntityError:
    def test_stores_identifier(self) -> None:
        err = DuplicateEntityError("Stream", "github:pull_request:project-123")
        assert err.context["entity_type"] == "Stream"
        assert err.context["identifier"] == "github:pull_request:project-123"

    def test_is_domain_error(self) -> None:
        assert isinstance(DuplicateEntityError("X", "y"), DomainError)


class TestValidationError:
    def test_stores_field_info(self) -> None:
        err = ValidationError("Stream", "source", "cannot be empty")
        assert err.context["entity_type"] == "Stream"
        assert err.context["field"] == "source"
        assert err.context["reason"] == "cannot be empty"

    def test_is_domain_error(self) -> None:
        assert isinstance(ValidationError("X", "f", "r"), DomainError)

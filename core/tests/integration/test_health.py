import os

import pytest
from httpx import ASGITransport, AsyncClient
from testcontainers.mongodb import MongoDbContainer

from core.infrastructure.web.app import create_app


@pytest.fixture
def test_app(mongo_container: MongoDbContainer, monkeypatch: pytest.MonkeyPatch):
    """Create a FastAPI app pointing at the testcontainers MongoDB."""
    url = mongo_container.get_connection_url()
    monkeypatch.setenv("MONGODB_URI", url)
    return create_app()


async def test_health_returns_ok(test_app):
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["mongodb"] == "connected"

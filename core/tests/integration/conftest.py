from collections.abc import AsyncGenerator

import pytest
from bson.codec_options import CodecOptions
from pymongo import AsyncMongoClient
from pymongo.asynchronous.database import AsyncDatabase
from testcontainers.mongodb import MongoDbContainer


@pytest.fixture(scope="session")
def mongo_container() -> MongoDbContainer:
    """Session-scoped: one MongoDB container for all integration tests."""
    container = MongoDbContainer("mongo:7")
    container.start()
    yield container  # type: ignore[misc]
    container.stop()


@pytest.fixture
async def mongo_db(mongo_container: MongoDbContainer) -> AsyncGenerator[AsyncDatabase]:
    """Function-scoped: clean database per test."""
    url = mongo_container.get_connection_url()
    client: AsyncMongoClient = AsyncMongoClient(url)
    db = client.get_database("test_stackstitch", codec_options=CodecOptions(tz_aware=True))
    yield db
    # Clean up: drop all collections after each test
    for name in await db.list_collection_names():
        await db.drop_collection(name)
    client.close()

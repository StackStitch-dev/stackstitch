from bson.codec_options import CodecOptions
from pymongo import AsyncMongoClient
from pymongo.asynchronous.database import AsyncDatabase


async def create_mongo_client(uri: str) -> AsyncMongoClient:
    """Create and return an AsyncMongoClient. Caller owns lifecycle (close)."""
    client: AsyncMongoClient = AsyncMongoClient(uri)
    return client


def get_database(client: AsyncMongoClient, db_name: str) -> AsyncDatabase:
    """Get a database reference from the client with tz-aware datetimes."""
    return client.get_database(db_name, codec_options=CodecOptions(tz_aware=True))

from fastapi import FastAPI
from pymongo import AsyncMongoClient
from pydantic_settings import BaseSettings


class CoreSettings(BaseSettings):
    mongodb_uri: str = "mongodb://localhost:27017/"
    mongodb_database: str = "stackstitch"

    model_config = {"env_prefix": ""}


def create_app() -> FastAPI:
    settings = CoreSettings()
    app = FastAPI(title="StackStitch Core", version="0.1.0")
    client: AsyncMongoClient | None = None

    @app.on_event("startup")
    async def startup() -> None:
        nonlocal client
        client = AsyncMongoClient(settings.mongodb_uri)

    @app.on_event("shutdown")
    async def shutdown() -> None:
        if client:
            client.close()

    @app.get("/health")
    async def health() -> dict[str, str]:
        if client is None:
            return {"status": "error", "detail": "no client"}
        try:
            await client.admin.command("ping")
            return {"status": "ok", "mongodb": "connected"}
        except Exception:
            return {"status": "degraded", "mongodb": "disconnected"}

    return app

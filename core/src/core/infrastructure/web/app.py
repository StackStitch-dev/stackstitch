from contextlib import asynccontextmanager

from fastapi import FastAPI
from pymongo import AsyncMongoClient
from pydantic_settings import BaseSettings


class CoreSettings(BaseSettings):
    mongodb_uri: str = "mongodb://localhost:27017/"
    mongodb_database: str = "stackstitch"

    model_config = {"env_prefix": ""}


def create_app() -> FastAPI:
    settings = CoreSettings()
    state: dict[str, AsyncMongoClient] = {}

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        state["client"] = AsyncMongoClient(settings.mongodb_uri)
        yield
        state["client"].close()

    app = FastAPI(title="StackStitch Core", version="0.1.0", lifespan=lifespan)

    @app.get("/health")
    async def health() -> dict[str, str]:
        client = state.get("client")
        if client is None:
            return {"status": "error", "detail": "no client"}
        try:
            await client.admin.command("ping")
            return {"status": "ok", "mongodb": "connected"}
        except Exception:
            return {"status": "degraded", "mongodb": "disconnected"}

    return app

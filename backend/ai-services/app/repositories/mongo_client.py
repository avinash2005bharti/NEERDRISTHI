from typing import Optional
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from ..config import settings
from ..observability.logger import logger

_client: Optional[AsyncIOMotorClient] = None
_db: Optional[AsyncIOMotorDatabase] = None


async def connect_to_mongo() -> Optional[AsyncIOMotorDatabase]:
    global _client, _db
    if not settings.is_mongo_configured:
        logger.warning("MONGODB_URI is not configured in agent-core. Running without persistent database.")
        return None

    try:
        _client = AsyncIOMotorClient(
            settings.MONGODB_URI,
            serverSelectionTimeoutMS=5000,
        )
        # Verify connection
        await _client.admin.command("ping")
        _db = _client[settings.MONGODB_DB_NAME]
        logger.info(f"Connected to MongoDB database '{settings.MONGODB_DB_NAME}' successfully.")
        return _db
    except Exception as e:
        logger.error(f"Failed to connect to MongoDB: {e}. Agent core will operate in in-memory mode.")
        _db = None
        return None


async def close_mongo_connection():
    global _client, _db
    if _client:
        _client.close()
        _client = None
        _db = None
        logger.info("MongoDB client connection closed.")


def get_db() -> Optional[AsyncIOMotorDatabase]:
    return _db

import sys
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Ensure backend/ai-services is in sys.path for direct script execution and IDE resolution
_pkg_root = str(Path(__file__).resolve().parents[1])
if _pkg_root not in sys.path:
    sys.path.insert(0, _pkg_root)

try:
    from .config import settings
    from .api.routes import router
    from .api.marine_map import router as marine_map_router
    from .memory.qdrant_service import qdrant_service
    from .gis.spatial_engine import spatial_engine
    from .cache.valkey_client import cache_client
    from .observability.logger import logger
except (ImportError, ValueError):
    from app.config import settings
    from app.api.routes import router
    from app.api.marine_map import router as marine_map_router
    from app.memory.qdrant_service import qdrant_service
    from app.gis.spatial_engine import spatial_engine
    from app.cache.valkey_client import cache_client
    from app.observability.logger import logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing ORCA Agent Core (Python AI & Spatial Services)...")

    # 1. Initialize Qdrant Cloud LTM collections if configured
    if settings.is_qdrant_configured:
        try:
            await qdrant_service.initialize_collections()
        except Exception as e:
            logger.warning(f"Failed initializing Qdrant collections: {e}")

    # 2. Test Valkey cache connection if configured
    if settings.is_valkey_configured:
        try:
            ok = await cache_client.ping()
            if ok:
                logger.info("Valkey cache connected and ready.")
            else:
                logger.warning("Valkey configured but ping failed. Cache will operate in memory/passthrough.")
        except Exception as e:
            logger.warning(f"Valkey initialization error: {e}. Continuing without cache.")

    # 3. Verify Deterministic GIS layers
    if spatial_engine.available:
        logger.info("GeoPandas/Shapely SpatialEngine layers verified.")
    else:
        logger.info("SpatialEngine active in algorithmic geometric mode.")

    logger.info("ORCA Agent Core initialized and ready.")
    yield

    logger.info("Shutting down ORCA Agent Core...")
    await cache_client.close()
    logger.info("Agent Core shutdown complete.")


app = FastAPI(
    title="ORCA Marine Agent Core (SIH26176)",
    description=(
        "Marine Ecosystem Reasoning with Collaborative Agents. "
        "LangGraph multi-agent orchestration for marine safety, PFZ discovery, "
        "GeoPandas spatial reasoning, isolated sandbox, and meteorological telemetry evaluation."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# CORS configuration — internal service protected by INTERNAL_SERVICE_SECRET header
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(marine_map_router)
app.include_router(router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.FASTAPI_HOST,
        port=settings.FASTAPI_PORT,
        reload=(settings.APP_ENV == "development"),
        log_level=settings.LOG_LEVEL.lower(),
    )

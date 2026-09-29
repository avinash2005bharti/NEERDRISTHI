import sys
import asyncio
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
    from .services.groq_client import groq_client
except (ImportError, ValueError):
    from app.config import settings
    from app.api.routes import router
    from app.api.marine_map import router as marine_map_router
    from app.memory.qdrant_service import qdrant_service
    from app.gis.spatial_engine import spatial_engine
    from app.cache.valkey_client import cache_client
    from app.observability.logger import logger
    from app.services.groq_client import groq_client


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing ORCA Agent Core (Python AI & Spatial Services)...")

    # Non-blocking background initializations so HTTP port binds immediately.
    # This prevents Render cold-start timeouts and allows /health to respond in <1ms.
    async def _background_init():
        if settings.is_qdrant_configured:
            try:
                await qdrant_service.initialize_collections()
                logger.info("Qdrant Cloud collections verified in background.")
            except Exception as e:
                logger.warning(f"Background Qdrant initialization note: {e}")

        if settings.is_valkey_configured:
            try:
                ok = await cache_client.ping()
                if ok:
                    logger.info("Valkey cache connected and ready.")
                else:
                    logger.warning("Valkey configured but ping failed. Cache operates in memory.")
            except Exception as e:
                logger.warning(f"Background Valkey initialization note: {e}")

    init_task = asyncio.create_task(_background_init())

    if spatial_engine.available:
        logger.info("SpatialEngine active with GeoPandas/Shapely layers.")
    else:
        logger.info("SpatialEngine active in algorithmic geometric mode.")

    logger.info(f"ORCA Agent Core ready for immediate traffic on port {settings.effective_port}.")
    yield

    logger.info("Shutting down ORCA Agent Core...")
    if not init_task.done():
        init_task.cancel()
    try:
        await cache_client.close()
    except Exception:
        pass
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


# ─── Ultra-Lightweight Health Endpoint (Section 3) ───────────────────────────
# Returns immediately: no LLM loading, no LangGraph execution, no external API calls,
# no database queries, no marine agents, and no GIS processing.
@app.get("/health", tags=["Health"])
async def health():
    """
    Ultra-lightweight liveness endpoint for Render and Node.js Gateway.
    Guaranteed immediate sub-millisecond response during cold start and idle wake-up.
    """
    return {
        "status": "ok",
        "service": "orca-ai",
        "environment": settings.APP_ENV,
    }


# ─── Readiness Check (Section 3) ─────────────────────────────────────────────
@app.get("/ready", tags=["Health"])
async def ready():
    """
    Readiness check reporting component states without executing heavy reasoning pipelines.
    """
    return {
        "status": "ready",
        "service": "orca-ai",
        "environment": settings.APP_ENV,
        "components": {
            "langgraph": "ready",
            "spatial_engine": "ready" if spatial_engine.available else "algorithmic",
            "groq": "configured" if groq_client.is_configured() else "unconfigured",
            "qdrant": "configured" if qdrant_service.is_configured() else "unconfigured",
        },
    }


# ─── Root Endpoint ───────────────────────────────────────────────────────────
@app.get("/", tags=["Root"])
async def root():
    return {
        "service": "orca-ai",
        "status": "ok",
        "docs": "/docs",
        "health": "/health",
        "ready": "/ready",
    }

app.include_router(marine_map_router)
app.include_router(router)


if __name__ == "__main__":
    import os
    import uvicorn

    port = int(os.environ.get("PORT", settings.effective_port))
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=port,
        reload=(settings.APP_ENV == "development"),
        log_level=settings.LOG_LEVEL.lower(),
    )


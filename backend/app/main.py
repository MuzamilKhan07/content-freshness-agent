import logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.app.api.contradiction_routes import contradiction_router
from backend.app.api.evidence_routes import router as evidence_router
from backend.app.api.remediation_routes import remediation_router
from backend.app.api.routes import router
from backend.app.core.config import settings

# Setup standard logger
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("freshguard.main")

app = FastAPI(
    title="FreshGuard AI API",
    description="Agentic content freshness and decay detection backend.",
    version="0.1.0",
)

from datetime import datetime, timezone
import os
from pathlib import Path
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

# CORS configuration
origins = list(
    set(
        [
            settings.FRONTEND_ORIGIN,
            *settings.ADDITIONAL_ALLOWED_ORIGINS,
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://localhost:3000",
            "http://127.0.0.1:3000",
        ]
    )
)

# In production or containerized environments, permit wildcard/matching origins
allow_all_origins = settings.ENVIRONMENT.lower() in ("production", "prod") or os.environ.get("K_SERVICE") is not None

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if allow_all_origins else origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Global safe error handling
@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    logger.error("Unhandled error processing request: %s", exc.__class__.__name__)
    return JSONResponse(
        status_code=500,
        content={"detail": "An internal server error occurred. Please contact the administrator."},
    )

# Register API Routers
app.include_router(router)
app.include_router(evidence_router)
app.include_router(contradiction_router)
app.include_router(remediation_router)


@app.get("/api/ready", tags=["Root"])
def readiness_check():
    """
    Readiness check reporting whether dataset inventory and core dependencies
    are initialized without executing external LLM calls or leaking secrets.
    """
    from backend.app.services.dataset_service import get_dataset_service
    ds = get_dataset_service()
    status = ds.get_status()
    if not status.available or status.record_count == 0:
        return JSONResponse(
            status_code=503,
            content={
                "status": "not_ready",
                "detail": "Dataset inventory is not yet loaded.",
                "available": False,
            },
        )
    return {
        "status": "ready",
        "service": "FreshGuard AI Backend",
        "records_loaded": status.record_count,
        "dataset_available": True,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# Static assets & SPA fallback for production deployment
dist_path = settings.resolve_frontend_dist_path()
if dist_path.exists() and (dist_path / "index.html").exists():
    logger.info(f"Serving production frontend assets from {dist_path}")
    assets_dir = dist_path / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

    @app.get("/{full_path:path}", tags=["Frontend SPA"])
    async def serve_spa(full_path: str):
        # Do not intercept API or documentation routes
        if full_path.startswith("api/") or full_path.startswith("docs") or full_path.startswith("openapi.json"):
            return JSONResponse(status_code=404, content={"detail": "Not Found"})

        # Check if requesting a direct static file in dist
        file_path = dist_path / full_path
        if file_path.is_file():
            return FileResponse(file_path)

        # Fallback to SPA index.html for client-side routing
        return FileResponse(dist_path / "index.html")
else:
    @app.get("/", tags=["Root"])
    def root():
        return {
            "service": "FreshGuard AI API",
            "status": "online",
            "documentation": "/docs",
            "health": "/api/health",
            "readiness": "/api/ready",
        }


if __name__ == "__main__":
    import uvicorn
    port = settings.get_effective_port()
    host = settings.BACKEND_HOST
    logger.info(f"Starting FreshGuard AI server on {host}:{port}")
    uvicorn.run(
        "backend.app.main:app",
        host=host,
        port=port,
        reload=settings.ENVIRONMENT == "development",
    )

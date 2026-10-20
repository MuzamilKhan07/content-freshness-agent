import logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.app.api.contradiction_routes import contradiction_router
from backend.app.api.evidence_routes import router as evidence_router
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

# Configure CORS for local development and Vite frontend
origins = list(
    set(
        [
            settings.FRONTEND_ORIGIN,
            *settings.ADDITIONAL_ALLOWED_ORIGINS,
            "http://localhost:5173",
            "http://127.0.0.1:5173",
        ]
    )
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
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

app.include_router(router)
app.include_router(evidence_router)
app.include_router(contradiction_router)


@app.get("/", tags=["Root"])
def root():
    return {
        "service": "FreshGuard AI API",
        "status": "online",
        "documentation": "/docs",
        "health": "/api/health",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.app.main:app",
        host=settings.BACKEND_HOST,
        port=settings.BACKEND_PORT,
        reload=True,
    )

"""FastAPI application entry point — ODRMitra"""

import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.config import settings
from src.core.logging import log, setup_logging
from src.core.exceptions import AppException
from src.api.routes import auth, disputes, documents, chat, voice, admin
from src.api.routes.channel import router as channel_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    log.info(f"Starting {settings.APP_NAME}...")
    setup_logging(debug=settings.DEBUG, log_format=settings.LOG_FORMAT)
    log.info(f"Environment: {settings.current_env}")

    # Sync skills from SKILL.md files to database
    try:
        from src.skills.sync import sync_skills_to_db
        from src.db.session import async_session_factory
        async with async_session_factory() as db:
            await sync_skills_to_db(db)
        log.info("Skills synced to database")
    except Exception as e:
        log.warning(f"Skill sync failed (non-fatal): {e}")

    yield

    log.info("Shutting down...")


app = FastAPI(
    title=settings.APP_NAME,
    description="AI-Enabled Virtual Negotiation Assistant for MSME Disputes",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def logging_middleware(request: Request, call_next):
    """Log all requests."""
    request_id = str(uuid.uuid4())[:8]
    start_time = time.time()
    request.state.request_id = request_id

    with log.contextualize(request_id=request_id):
        log.info(
            "Request started",
            method=request.method,
            path=request.url.path,
        )
        response = await call_next(request)
        duration_ms = (time.time() - start_time) * 1000
        log.info(
            "Request completed",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=round(duration_ms, 2),
        )

    return response


@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    """Handle application exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.message, "details": exc.details},
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions."""
    log.exception("Unhandled exception")
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error"},
    )


# Routes
app.include_router(auth.router, prefix=f"{settings.API_PREFIX}/auth", tags=["auth"])
app.include_router(disputes.router, prefix=f"{settings.API_PREFIX}/disputes", tags=["disputes"])
app.include_router(documents.router, prefix=f"{settings.API_PREFIX}/disputes", tags=["documents"])
app.include_router(chat.router, prefix=f"{settings.API_PREFIX}/chat", tags=["chat"])
app.include_router(voice.router, prefix=f"{settings.API_PREFIX}/voice", tags=["voice"])
app.include_router(channel_router, prefix=f"{settings.API_PREFIX}", tags=["channels"])
app.include_router(admin.router, prefix=f"{settings.API_PREFIX}/admin", tags=["admin"])


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "app": settings.APP_NAME}


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "app": settings.APP_NAME,
        "version": "0.1.0",
        "docs": "/docs" if settings.DEBUG else None,
    }

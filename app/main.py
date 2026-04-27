from contextlib import asynccontextmanager
import httpx
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded

from app.database import init_db, engine
from app.middleware.logging import request_logging_middleware
from app.middleware.rate_limit import limiter
from app.routers.api_v1 import auth, profiles, export


# -----------------------------
# Lifespan (startup/shutdown)
# -----------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    app.state.http_client = httpx.AsyncClient(timeout=10.0)
    yield
    await app.state.http_client.aclose()
    engine.dispose()


# -----------------------------
# App Init
# -----------------------------
app = FastAPI(
    title="Insighta Labs+",
    description="Profile Intelligence System - Stage 3",
    version="3.0.0",
    lifespan=lifespan,
)

# -----------------------------
# CORS
# -----------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------------
# Middleware
# -----------------------------
app.middleware("http")(request_logging_middleware)

app.state.limiter = limiter


# -----------------------------
# Exception Handlers
# -----------------------------
@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=400,
        content={"status": "error", "message": "Invalid request parameters"},
    )


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=429,
        content={"status": "error", "message": "Rate limit exceeded"},
    )


@app.exception_handler(Exception)
async def global_error_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"status": "error", "message": "Internal server error"},
    )


# -----------------------------
# Routers (Stage 3 API)
# -----------------------------
app.include_router(auth.router, prefix="/api/v1")
app.include_router(profiles.router, prefix="/api/v1")
app.include_router(export.router, prefix="/api/v1")


# -----------------------------
# Health Routes
# -----------------------------
@app.get("/")
async def root():
    return {
        "app": "Insighta Labs+",
        "version": "3.0.0",
        "status": "running",
    }


@app.get("/health")
async def health():
    return {"status": "healthy"}

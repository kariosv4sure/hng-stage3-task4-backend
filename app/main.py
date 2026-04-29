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
from app.seed import seed_profiles


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize DB
    init_db()

    # Seed Stage 2 data into Stage 3 DB
    seed_profiles()

    # HTTP client
    app.state.http_client = httpx.AsyncClient(timeout=10.0)

    yield

    await app.state.http_client.aclose()
    engine.dispose()


app = FastAPI(
    title="Insighta Labs+",
    description="Profile Intelligence System - Stage 3",
    version="3.0.0",
    lifespan=lifespan,
)

# CORS (frontend access)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://hng-stage3-task4-web.vercel.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Logging middleware
app.middleware("http")(request_logging_middleware)

# Rate limiter
app.state.limiter = limiter


# ----------------------------
# Exception Handlers
# ----------------------------

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


# ----------------------------
# Routes
# ----------------------------

app.include_router(auth.router, prefix="/api/v1")
app.include_router(profiles.router, prefix="/api/v1")
app.include_router(export.router, prefix="/api/v1")


@app.get("/")
async def root():
    return {
        "app": "Insighta Labs+",
        "version": "3.0.0",
        "status": "running"
    }


@app.get("/health")
async def health():
    return {"status": "healthy"}

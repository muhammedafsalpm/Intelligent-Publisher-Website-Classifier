from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import time
from app.api import classify
from app.models import HealthResponse
from app.utils.cache import cache
from app.services.rag import PolicyStore
from app.config import settings
from app.utils.logger import logger

# Rate limiting
limiter = Limiter(key_func=get_remote_address)

# Create FastAPI app
app = FastAPI(
    title=settings.api_title,
    version=settings.api_version,
    docs_url="/docs" if settings.debug else None
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(classify.router, prefix="/api", tags=["classification"])

@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    logger.info("Starting Publisher Classifier API...")
    await cache.connect()
    logger.info("API ready")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("Shutting down...")
    await cache.close()

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    policy_store = PolicyStore()
    return HealthResponse(
        status="healthy",
        model=settings.llm_model,
        policies_loaded=policy_store.collection.count(),
        redis_connected=cache._connected
    )

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "Publisher Website Classifier",
        "version": settings.api_version,
        "docs": "/docs" if settings.debug else "disabled in production"
    }

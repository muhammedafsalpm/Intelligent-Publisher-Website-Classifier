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
from app.services.llm.factory import llm_factory
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
    logger.info(f"Starting Publisher Classifier API with LLM provider: {settings.llm_provider}")
    await cache.connect()
    
    # Initialize LLM client
    llm_factory.get_client()
    
    # Initialize policy store
    policy_store = PolicyStore()
    
    logger.info(f"API ready - Provider: {settings.llm_provider}, Model: {settings.openai_model if settings.llm_provider == 'openai' else settings.ollama_model}")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("Shutting down...")
    await cache.close()
    await llm_factory.close()

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    policy_store = PolicyStore()
    
    # Check LLM provider health
    llm_healthy = True
    try:
        client = llm_factory.get_client()
        # Simple test
        await client.chat_completion(
            messages=[{"role": "user", "content": "test"}],
            response_format="text"
        )
    except Exception as e:
        llm_healthy = False
        logger.error(f"LLM provider {settings.llm_provider} health check failed: {e}")
    
    return HealthResponse(
        status="healthy" if llm_healthy else "degraded",
        model=settings.openai_model if settings.llm_provider == "openai" else settings.ollama_model,
        policies_loaded=policy_store.collection.count(),
        redis_connected=cache._connected,
        llm_provider=settings.llm_provider,
        llm_healthy=llm_healthy
    )

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "Publisher Website Classifier",
        "version": settings.api_version,
        "llm_provider": settings.llm_provider,
        "model": settings.openai_model if settings.llm_provider == "openai" else settings.ollama_model,
        "docs": "/docs" if settings.debug else "disabled in production"
    }

from contextlib import asynccontextmanager
import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings

logger = structlog.get_logger()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup lifecycle
    logger.info("ZF-Core initial startup", env=settings.APP_ENV)
    yield
    # Shutdown lifecycle
    logger.info("ZF-Core graceful shutdown")

app = FastAPI(
    title="ZF-Core V19.0",
    version="19.0.0",
    lifespan=lifespan
)

# CORS middleware config
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict in production setup
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/health")
async def health_check():
    return {
        "status": "healthy",
        "version": app.version
    }

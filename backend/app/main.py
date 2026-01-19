"""
MLB Contract Advisor - FastAPI Backend
======================================
AI-powered MLB contract prediction API.
"""
import logging
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from app.config import (
    API_V1_PREFIX,
    PROJECT_NAME,
    VERSION,
    ALLOWED_ORIGINS,
    BASE_DIR,
    MODELS_DIR,
    DATABASE_URL,
    RATE_LIMIT,
)
from app.models.database import init_db, SessionLocal, engine
from app.models.schemas import HealthResponse
from app.services.prediction_service import prediction_service
from app.api import predictions, players, contracts

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Configure rate limiter
limiter = Limiter(key_func=get_remote_address)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown events."""
    # Startup
    logger.info("Starting MLB Contract Advisor API...")
    logger.debug("BASE_DIR: %s", BASE_DIR)
    logger.debug("MODELS_DIR: %s", MODELS_DIR)
    logger.debug("Models dir exists: %s", MODELS_DIR.exists())
    if MODELS_DIR.exists():
        logger.debug("Models dir contents: %s", os.listdir(MODELS_DIR))

    # Initialize database
    logger.info("Initializing database...")
    init_db()

    # Load ML models
    logger.info("Loading ML models...")
    if prediction_service.load_models():
        logger.info("Loaded %d models successfully", len(prediction_service.models))
    else:
        logger.warning("Failed to load some models")

    # Stats service uses on-demand fetching via pybaseball (no CSV loading needed)
    logger.info("Stats service ready (on-demand fetching via pybaseball)")

    yield

    # Shutdown
    logger.info("Shutting down...")


# Create FastAPI app
app = FastAPI(
    title=PROJECT_NAME,
    version=VERSION,
    description="""
    MLB Contract Advisor API - Predict MLB player contract values using machine learning.

    ## Features
    - **Predictions**: Get AI-powered contract predictions with confidence scores
    - **Comparables**: Find similar historical contracts
    - **Database**: Search 450+ historical MLB contracts (2015-2026)
    - **Transparency**: Full feature importance breakdown

    ## Model Performance
    - Accuracy within $5M: 73-74%
    - Separate models for batters and pitchers

    ## Rate Limiting
    - 100 requests per hour per IP address
    """,
    lifespan=lifespan,
)

# Add rate limiter state and exception handler
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(predictions.router, prefix=API_V1_PREFIX)
app.include_router(players.router, prefix=API_V1_PREFIX)
app.include_router(contracts.router, prefix=API_V1_PREFIX)


@app.get("/", tags=["Root"])
async def root():
    """API root - redirects to docs."""
    return {
        "message": "MLB Contract Advisor API",
        "version": VERSION,
        "docs": "/docs",
        "health": "/health"
    }


@app.get("/debug", tags=["Debug"])
async def debug_info():
    """Debug information about the deployment."""
    import sys
    import sklearn
    import numpy
    import pandas
    import pydantic

    # Check if models have required features
    model_info = {}
    for name, model in prediction_service.models.items():
        model_info[name] = {
            "type": type(model).__name__,
            "features_count": len(prediction_service.features.get(name, [])),
        }

    # Check database
    db_info = {}
    try:
        db = SessionLocal()
        from sqlalchemy import text, inspect
        inspector = inspect(engine)
        columns = [c['name'] for c in inspector.get_columns('contracts')]
        db_info["contracts_columns"] = columns
        db_info["has_recent_war_3yr"] = "recent_war_3yr" in columns
        db.close()
    except Exception as e:
        db_info["error"] = str(e)

    return {
        "python_version": sys.version,
        "sklearn_version": sklearn.__version__,
        "numpy_version": numpy.__version__,
        "pandas_version": pandas.__version__,
        "pydantic_version": pydantic.__version__,
        "models_loaded": prediction_service.is_loaded,
        "models_info": model_info,
        "database_info": db_info,
    }


@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """Check API health status."""
    # Check database connection
    db_connected = False
    db = None
    try:
        from sqlalchemy import text
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db_connected = True
    except Exception as e:
        logger.warning("Database health check failed: %s", e)
    finally:
        if db:
            db.close()

    return HealthResponse(
        status="ok" if prediction_service.is_loaded else "degraded",
        version=VERSION,
        models_loaded=prediction_service.is_loaded,
        database_connected=db_connected
    )

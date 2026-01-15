"""
MLB Contract Advisor - FastAPI Backend
======================================
AI-powered MLB contract prediction API.
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import (
    API_V1_PREFIX,
    PROJECT_NAME,
    VERSION,
    ALLOWED_ORIGINS,
    BASE_DIR,
    MODELS_DIR,
    DATABASE_URL
)
from app.models.database import init_db, SessionLocal
from app.models.schemas import HealthResponse
from app.services.prediction_service import prediction_service
from app.api import predictions, players, contracts


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown events."""
    # Startup
    print("Starting MLB Contract Advisor API...")
    print(f"BASE_DIR: {BASE_DIR}")
    print(f"MODELS_DIR: {MODELS_DIR}")
    print(f"DATABASE_URL: {DATABASE_URL}")
    print(f"Models dir exists: {MODELS_DIR.exists()}")
    if MODELS_DIR.exists():
        import os
        print(f"Models dir contents: {os.listdir(MODELS_DIR)}")

    # Initialize database
    print("Initializing database...")
    init_db()

    # Load ML models
    print("Loading ML models...")
    if prediction_service.load_models():
        print(f"Loaded {len(prediction_service.models)} models successfully")
    else:
        print("Warning: Failed to load some models")

    yield

    # Shutdown
    print("Shutting down...")


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
    """,
    lifespan=lifespan,
)

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


@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """Check API health status."""
    # Check database connection
    db_connected = False
    try:
        from sqlalchemy import text
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db_connected = True
        db.close()
    except:
        pass

    return HealthResponse(
        status="ok" if prediction_service.is_loaded else "degraded",
        version=VERSION,
        models_loaded=prediction_service.is_loaded,
        database_connected=db_connected
    )

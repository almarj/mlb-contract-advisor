"""
Application configuration settings.
"""
import os
from pathlib import Path

# Base paths
BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "Data"
MODELS_DIR = DATA_DIR / "Models"
MASTER_DATA_DIR = DATA_DIR / "Master Data"

# Database
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR}/mlb_contracts.db")

# API Settings
API_V1_PREFIX = "/api/v1"
PROJECT_NAME = "MLB Contract Advisor API"
VERSION = "1.0.0"

# Rate limiting
RATE_LIMIT = "100/hour"

# CORS - Configure via ALLOWED_ORIGINS env var (comma-separated) or use defaults
# For Railway: Set ALLOWED_ORIGINS to your frontend Railway URL
_default_origins = [
    "http://localhost:3000",
    "http://localhost:5173",
]
_env_origins = os.getenv("ALLOWED_ORIGINS", "")
ALLOWED_ORIGINS = [o.strip() for o in _env_origins.split(",") if o.strip()] if _env_origins else _default_origins

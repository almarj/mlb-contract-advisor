"""
Application configuration settings.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file
load_dotenv()

# Base paths
BASE_DIR = Path(__file__).resolve().parent.parent  # backend folder
MODELS_DIR = BASE_DIR / "models"  # backend/models folder
MASTER_DATA_DIR = BASE_DIR  # For CSV files (not used in deployment)

# Database
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR}/mlb_contracts.db")

# API Settings
API_V1_PREFIX = "/api/v1"
PROJECT_NAME = "MLB Contract Advisor API"
VERSION = "1.0.0"

# Rate limiting
RATE_LIMIT = "100/hour"
CHAT_RATE_LIMIT = "50/hour"  # Stricter for Claude API calls

# Anthropic Claude API
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-20250514")
CLAUDE_TIMEOUT = int(os.getenv("CLAUDE_TIMEOUT", "25"))  # seconds

# Admin secret for protected operations (reseed, etc.)
ADMIN_SECRET = os.getenv("ADMIN_SECRET", "")

# CORS - Configure via ALLOWED_ORIGINS env var (comma-separated) or use defaults
# For Railway: Set ALLOWED_ORIGINS to your frontend Railway URL
_default_origins = [
    "http://localhost:3000",
    "http://localhost:5173",
]
_env_origins = os.getenv("ALLOWED_ORIGINS", "")
ALLOWED_ORIGINS = [o.strip() for o in _env_origins.split(",") if o.strip()] if _env_origins else _default_origins

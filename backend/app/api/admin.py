"""
Admin API endpoints - Protected operations like reseeding the database.
"""
import logging
import secrets
import subprocess
import sys
from fastapi import APIRouter, HTTPException, Header, Request
from pydantic import BaseModel
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.config import ADMIN_SECRET, BASE_DIR

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["Admin"])

# Strict rate limiting for admin endpoints (5 requests per hour)
limiter = Limiter(key_func=get_remote_address)


class ReseedResponse(BaseModel):
    success: bool
    message: str


@router.post("/reseed", response_model=ReseedResponse)
@limiter.limit("5/hour")
async def reseed_database(
    request: Request,
    x_admin_secret: str = Header(..., description="Admin secret key")
):
    """
    Reseed the database with fresh data from master CSV.

    Requires ADMIN_SECRET environment variable to be set and passed in header.
    """
    # Validate admin secret
    if not ADMIN_SECRET:
        raise HTTPException(
            status_code=503,
            detail="Admin operations not configured. Set ADMIN_SECRET env var."
        )

    if not secrets.compare_digest(x_admin_secret, ADMIN_SECRET):
        raise HTTPException(status_code=403, detail="Invalid admin secret")

    logger.info("Starting database reseed...")

    try:
        # Run the seed script
        seed_script = BASE_DIR / "seed_database.py"

        if not seed_script.exists():
            raise HTTPException(
                status_code=500,
                detail=f"Seed script not found at {seed_script}"
            )

        result = subprocess.run(
            [sys.executable, str(seed_script)],
            cwd=str(BASE_DIR),
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )

        if result.returncode != 0:
            logger.error(f"Reseed failed: {result.stderr}")
            raise HTTPException(
                status_code=500,
                detail="Reseed failed. Check server logs for details."
            )

        logger.info("Database reseed completed successfully")
        return ReseedResponse(
            success=True,
            message="Database reseeded successfully"
        )

    except subprocess.TimeoutExpired:
        raise HTTPException(
            status_code=504,
            detail="Reseed timed out after 5 minutes"
        )
    except Exception as e:
        logger.error(f"Reseed error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Reseed error: {str(e)}"
        )

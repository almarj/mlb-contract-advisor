"""
Prediction API endpoints.
"""
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.models.schemas import PredictionRequest, PredictionResponse
from app.models.database import get_db, Contract
from app.services.prediction_service import prediction_service

router = APIRouter(prefix="/predictions", tags=["Predictions"])


def normalize_name(name: str) -> str:
    """Normalize player name for matching."""
    import unicodedata
    import re
    if not name:
        return ""
    # Remove accents
    name = unicodedata.normalize('NFD', name)
    name = ''.join(c for c in name if unicodedata.category(c) != 'Mn')
    # Remove suffixes
    suffixes = [' jr.', ' jr', ' sr.', ' sr', ' ii', ' iii', ' iv', ' v']
    name_lower = name.lower()
    for suffix in suffixes:
        if name_lower.endswith(suffix):
            name = name[:-len(suffix)]
            break
    name = re.sub(r"[^\w\s\-]", "", name)
    return ' '.join(name.split()).lower().strip()


@router.post("", response_model=PredictionResponse)
async def create_prediction(request: PredictionRequest, db: Session = Depends(get_db)):
    """
    Generate a contract prediction for a player.

    Requires player stats (3-year averages) and returns:
    - Predicted AAV (with low/high range)
    - Predicted contract length
    - Confidence score
    - Comparable players
    - Feature importance breakdown
    - Actual AAV/length if player has signed a contract
    """
    if not prediction_service.is_loaded:
        raise HTTPException(
            status_code=503,
            detail="ML models not loaded. Please try again later."
        )

    try:
        # Validate required fields based on position
        is_pitcher = prediction_service.is_pitcher(request.position)

        if is_pitcher:
            if request.era_3yr is None and request.fip_3yr is None:
                raise HTTPException(
                    status_code=400,
                    detail="Pitchers require ERA or FIP stats"
                )
        else:
            if request.wrc_plus_3yr is None and request.avg_3yr is None:
                raise HTTPException(
                    status_code=400,
                    detail="Batters require wRC+ or batting average stats"
                )

        # Make prediction
        result = prediction_service.predict(request)

        # Look up actual contract for this player (if exists)
        actual_aav = None
        actual_length = None

        if request.name:
            # Try exact match first, then normalized match
            contract = db.query(Contract).filter(
                Contract.player_name.ilike(request.name)
            ).order_by(desc(Contract.year_signed)).first()

            if not contract:
                # Try normalized name match
                normalized_input = normalize_name(request.name)
                all_contracts = db.query(Contract).all()
                for c in all_contracts:
                    if normalize_name(c.player_name) == normalized_input:
                        contract = c
                        break

            if contract:
                actual_aav = contract.aav
                actual_length = contract.length

        return PredictionResponse(
            player_name=request.name,
            position=request.position,
            predicted_aav=result['predicted_aav'] * 1_000_000,  # Convert to dollars
            predicted_aav_low=result['predicted_aav_low'] * 1_000_000,
            predicted_aav_high=result['predicted_aav_high'] * 1_000_000,
            predicted_length=result['predicted_length'],
            actual_aav=actual_aav,
            actual_length=actual_length,
            confidence_score=result['confidence_score'],
            comparables=result['comparables'],
            feature_importance=result['feature_importance'],
            model_accuracy=result['model_accuracy'],
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Prediction failed: {str(e)}"
        )

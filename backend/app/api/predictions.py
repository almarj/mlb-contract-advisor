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
        signing_war_3yr = None
        signing_wrc_plus_3yr = None
        signing_era_3yr = None
        recent_war_3yr = None
        recent_wrc_plus_3yr = None
        recent_era_3yr = None
        contract = None

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

                # Stats at signing (pre-signing 3yr averages)
                signing_war_3yr = contract.war_3yr
                signing_wrc_plus_3yr = contract.wrc_plus_3yr
                signing_era_3yr = contract.era_3yr

                # Recent performance stats
                recent_war_3yr = contract.recent_war_3yr
                recent_wrc_plus_3yr = contract.recent_wrc_plus_3yr
                recent_era_3yr = contract.recent_era_3yr

        # Calculate predicted AAV based on recent performance (if available)
        predicted_aav_recent = None
        if contract and contract.recent_war_3yr is not None:
            # Build a request with recent stats to get model prediction
            is_pitcher = prediction_service.is_pitcher(request.position)
            if is_pitcher:
                recent_request = PredictionRequest(
                    name=request.name,
                    position=request.position,
                    age=request.age,  # Use current age from form
                    war_3yr=contract.recent_war_3yr or 0,
                    era_3yr=contract.recent_era_3yr,
                    fip_3yr=contract.recent_fip_3yr,
                    k_9_3yr=contract.recent_k_9_3yr,
                    bb_9_3yr=contract.recent_bb_9_3yr,
                    ip_3yr=contract.recent_ip_3yr,
                )
            else:
                recent_request = PredictionRequest(
                    name=request.name,
                    position=request.position,
                    age=request.age,  # Use current age from form
                    war_3yr=contract.recent_war_3yr or 0,
                    wrc_plus_3yr=contract.recent_wrc_plus_3yr,
                    avg_3yr=contract.recent_avg_3yr,
                    obp_3yr=contract.recent_obp_3yr,
                    slg_3yr=contract.recent_slg_3yr,
                    hr_3yr=contract.recent_hr_3yr,
                )
            recent_result = prediction_service.predict(recent_request)
            predicted_aav_recent = recent_result['predicted_aav'] * 1_000_000

        return PredictionResponse(
            player_name=request.name,
            position=request.position,
            predicted_aav=result['predicted_aav'] * 1_000_000,  # Convert to dollars
            predicted_aav_low=result['predicted_aav_low'] * 1_000_000,
            predicted_aav_high=result['predicted_aav_high'] * 1_000_000,
            predicted_length=result['predicted_length'],
            actual_aav=actual_aav,
            actual_length=actual_length,
            signing_war_3yr=signing_war_3yr,
            signing_wrc_plus_3yr=signing_wrc_plus_3yr,
            signing_era_3yr=signing_era_3yr,
            recent_war_3yr=recent_war_3yr,
            recent_wrc_plus_3yr=recent_wrc_plus_3yr,
            recent_era_3yr=recent_era_3yr,
            predicted_aav_recent=predicted_aav_recent,
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

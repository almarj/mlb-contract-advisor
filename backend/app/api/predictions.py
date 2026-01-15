"""
Prediction API endpoints.
"""
from fastapi import APIRouter, HTTPException
from app.models.schemas import PredictionRequest, PredictionResponse
from app.services.prediction_service import prediction_service

router = APIRouter(prefix="/predictions", tags=["Predictions"])


@router.post("", response_model=PredictionResponse)
async def create_prediction(request: PredictionRequest):
    """
    Generate a contract prediction for a player.

    Requires player stats (3-year averages) and returns:
    - Predicted AAV (with low/high range)
    - Predicted contract length
    - Confidence score
    - Comparable players
    - Feature importance breakdown
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

        return PredictionResponse(
            player_name=request.name,
            position=request.position,
            predicted_aav=result['predicted_aav'] * 1_000_000,  # Convert to dollars
            predicted_aav_low=result['predicted_aav_low'] * 1_000_000,
            predicted_aav_high=result['predicted_aav_high'] * 1_000_000,
            predicted_length=result['predicted_length'],
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

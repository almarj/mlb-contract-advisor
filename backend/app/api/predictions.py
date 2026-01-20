"""
Prediction API endpoints.
"""
import logging
from typing import List
from fastapi import APIRouter, HTTPException, Depends, Request
from sqlalchemy.orm import Session
from sqlalchemy import desc, func

from app.models.schemas import PredictionRequest, PredictionResponse, ComparablePlayer
from app.models.database import get_db, Contract
from app.services.prediction_service import prediction_service
from app.config import RATE_LIMIT
from app.utils import (
    normalize_name,
    is_pitcher as check_is_pitcher,
    get_position_group,
    get_current_year,
    PITCHER_POSITIONS,
    POSITION_GROUPS,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/predictions", tags=["Predictions"])


def find_comparables_by_recent_performance(
    db: Session,
    target_recent_war: float,
    position: str,
    current_age: int,
    n: int = 5
) -> List[ComparablePlayer]:
    """
    Find comparable players based on their RECENT performance (2023-2025 stats).

    This compares the target player's recent WAR against other players' recent WAR,
    showing who is performing at a similar level RIGHT NOW.
    """
    position_is_pitcher = check_is_pitcher(position)
    current_year = get_current_year()

    # Filter by player type in the database query (not in Python)
    query = db.query(Contract).filter(Contract.recent_war_3yr.isnot(None))

    if position_is_pitcher:
        query = query.filter(Contract.position.in_(PITCHER_POSITIONS))
    else:
        query = query.filter(Contract.position.notin_(PITCHER_POSITIONS))

    contracts = query.all()

    if not contracts:
        return []

    # Calculate similarity scores based on RECENT performance
    # Weight: 40% position, 35% recent WAR, 15% age, 10% recency of contract
    scored_contracts = []
    pos_group = get_position_group(position)

    # Get max values for normalization
    war_diffs = [abs(c.recent_war_3yr - target_recent_war) for c in contracts]
    max_war_diff = max(war_diffs) if max(war_diffs) > 0 else 1

    age_diffs = [abs(c.age_at_signing - current_age) for c in contracts]
    max_age_diff = max(age_diffs) if max(age_diffs) > 0 else 1

    year_diffs = [current_year - c.year_signed for c in contracts]
    max_year_diff = max(year_diffs) if max(year_diffs) > 0 else 1

    for contract in contracts:
        similarity = 0.0

        # Position similarity (40%)
        contract_pos_group = get_position_group(contract.position)
        if contract_pos_group == pos_group:
            similarity += 40

        # Recent WAR similarity (35%) - comparing recent performance to recent performance
        war_diff = abs(contract.recent_war_3yr - target_recent_war)
        similarity += (1 - war_diff / max_war_diff) * 35

        # Age similarity (15%)
        age_diff = abs(contract.age_at_signing - current_age)
        similarity += (1 - age_diff / max_age_diff) * 15

        # Recency (10%)
        year_diff = current_year - contract.year_signed
        similarity += (1 - year_diff / max_year_diff) * 10

        scored_contracts.append((contract, similarity))

    # Sort by similarity and take top n
    scored_contracts.sort(key=lambda x: -x[1])
    top_contracts = scored_contracts[:n]

    comparables = []
    for contract, similarity in top_contracts:
        age = contract.age_at_signing
        length = contract.length
        # Pre-FA extension: young player (<=25) with long contract (>=6 years)
        is_ext = age <= 25 and length >= 6

        comparables.append(ComparablePlayer(
            name=contract.player_name,
            position=contract.position,
            signing_team=contract.signing_team,
            year_signed=contract.year_signed,
            age_at_signing=age,
            aav=contract.aav,
            length=length,
            war_3yr=contract.recent_war_3yr,  # Show RECENT WAR, not at-signing WAR
            similarity_score=round(similarity, 1),
            is_extension=is_ext,
        ))

    return comparables


@router.post("", response_model=PredictionResponse)
async def create_prediction(request_obj: Request, request: PredictionRequest, db: Session = Depends(get_db)):
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
            # Try exact match first (case-insensitive)
            contract = db.query(Contract).filter(
                Contract.player_name.ilike(request.name)
            ).order_by(desc(Contract.year_signed)).first()

            if not contract:
                # Try normalized name match using LIKE with wildcards
                # This handles accents and suffixes better than exact match
                normalized_input = normalize_name(request.name)
                # Split into parts for flexible matching
                name_parts = normalized_input.split()
                if name_parts:
                    # Match on first and last name parts
                    query = db.query(Contract)
                    for part in name_parts:
                        query = query.filter(
                            func.lower(Contract.player_name).contains(part)
                        )
                    contract = query.order_by(desc(Contract.year_signed)).first()

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
        comparables_recent = []
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

            # Find comparables based on RECENT performance (comparing recent WAR to recent WAR)
            comparables_recent = find_comparables_by_recent_performance(
                db=db,
                target_recent_war=contract.recent_war_3yr,
                position=request.position,
                current_age=request.age,
                n=5
            )

        return PredictionResponse(
            player_name=request.name,
            position=request.position,
            signing_team=contract.signing_team if contract else None,
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
            comparables_recent=comparables_recent,
            feature_importance=result['feature_importance'],
            model_accuracy=result['model_accuracy'],
        )

    except HTTPException:
        raise
    except Exception as e:
        # Log the full error for debugging
        import traceback
        error_trace = traceback.format_exc()
        logger.exception("Prediction failed for player %s: %s\n%s", request.name, str(e), error_trace)
        # Return detailed error in development/debug mode
        raise HTTPException(
            status_code=500,
            detail=f"Prediction error: {str(e)}"
        )

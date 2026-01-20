"""
Chat API endpoint - Natural language queries about player contracts.
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.config import CHAT_RATE_LIMIT
from app.models.database import get_db, Player, Contract
from app.models.schemas import (
    ChatRequest,
    ChatResponse,
    ChatAction,
    ChatActionType,
    PredictionRequest,
    PredictionResponse,
    TwoWayPrediction,
)
from app.services.claude_service import claude_service
from app.services.context_service import context_service
from app.services.sanitize_service import sanitize_service
from app.services.prediction_service import prediction_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["Chat"])

# Rate limiter for chat endpoint (stricter than general API)
limiter = Limiter(key_func=get_remote_address)


@router.post("/query", response_model=ChatResponse)
@limiter.limit(CHAT_RATE_LIMIT)
async def process_chat_query(
    request: Request,
    chat_request: ChatRequest,
    db: Session = Depends(get_db)
):
    """
    Process a natural language query about MLB contracts.

    This endpoint:
    1. Sanitizes the user's query
    2. Extracts player name from natural language
    3. Runs the ML model prediction if player found
    4. Uses Claude to explain the prediction
    5. Returns structured response with actions

    Rate limited to 50 requests/hour per IP.
    """
    # Step 1: Sanitize the query
    sanitized_query, is_valid, error_msg = sanitize_service.sanitize_query(
        chat_request.query
    )

    if not is_valid:
        raise HTTPException(status_code=400, detail=error_msg)

    logger.info(f"Processing chat query: {sanitized_query[:100]}...")

    # Step 2: Extract player name from query
    player_name, suggestions = context_service.extract_player_name(
        sanitized_query, db
    )

    # If no player found, return helpful response
    if not player_name:
        context = context_service.build_not_found_context(
            sanitized_query, suggestions
        )
        claude_result = await claude_service.generate_explanation(
            sanitized_query, context
        )

        return ChatResponse(
            response=claude_result["explanation"],
            prediction=None,
            actions=[
                ChatAction(
                    action_type=ChatActionType.SHOW_CONTRACTS,
                    parameters={}
                )
            ],
            player_found=False,
            player_name=None,
            suggestions=suggestions,
            claude_available=claude_result["success"],
            used_fallback=claude_result["used_fallback"]
        )

    # Step 3: Get player data and run prediction
    try:
        prediction_response = await _get_prediction_for_player(
            player_name, db
        )
    except Exception as e:
        logger.error(f"Error getting prediction for {player_name}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate prediction for {player_name}"
        )

    # Step 4: Build context and get Claude explanation
    # Check if this is a two-way player (like Ohtani)
    is_two_way = context_service.is_two_way_player(player_name, db)
    two_way_predictions = None
    combined_aav = None

    if is_two_way:
        # Get separate predictions for batting and pitching
        context, two_way_predictions, combined_aav = await _build_two_way_context(
            player_name,
            prediction_response,
            db
        )
    else:
        context = context_service.build_prediction_context(
            prediction_response,
            player_name,
            prediction_response.position
        )

    # Add player stats context for stats-related questions
    stats_context = context_service.build_stats_context(player_name, db)
    if stats_context:
        context += stats_context

    claude_result = await claude_service.generate_explanation(
        sanitized_query, context
    )

    # Step 5: Build response with actions
    actions = _build_actions_from_claude(
        claude_result["actions"],
        player_name
    )

    # Ensure we always have a view_prediction action
    has_view_action = any(
        a.action_type == ChatActionType.VIEW_PREDICTION for a in actions
    )
    if not has_view_action:
        actions.insert(0, ChatAction(
            action_type=ChatActionType.VIEW_PREDICTION,
            target_player=player_name
        ))

    return ChatResponse(
        response=claude_result["explanation"],
        prediction=prediction_response,
        actions=actions,
        player_found=True,
        player_name=player_name,
        suggestions=suggestions,
        is_two_way_player=is_two_way,
        two_way_predictions=two_way_predictions,
        combined_aav=combined_aav,
        claude_available=claude_result["success"],
        used_fallback=claude_result["used_fallback"]
    )


async def _get_prediction_for_player(
    player_name: str,
    db: Session
) -> PredictionResponse:
    """
    Get a full prediction for a player by name.

    Looks up player data from database and runs prediction.
    """
    # First try to find in contracts (signed players)
    contract = db.query(Contract).filter(
        Contract.player_name.ilike(player_name)
    ).order_by(Contract.year_signed.desc()).first()

    if contract:
        # Build prediction request from contract data
        pred_request = PredictionRequest(
            name=contract.player_name,
            position=contract.position,
            age=contract.age_at_signing,
            war_3yr=contract.war_3yr or 2.0,
            wrc_plus_3yr=contract.wrc_plus_3yr,
            avg_3yr=contract.avg_3yr,
            obp_3yr=contract.obp_3yr,
            slg_3yr=contract.slg_3yr,
            hr_3yr=contract.hr_3yr,
            era_3yr=contract.era_3yr,
            fip_3yr=contract.fip_3yr,
            k_9_3yr=contract.k_9_3yr,
            bb_9_3yr=contract.bb_9_3yr,
            ip_3yr=contract.ip_3yr,
            avg_exit_velo=contract.avg_exit_velo,
            barrel_rate=contract.barrel_rate,
            max_exit_velo=contract.max_exit_velo,
            hard_hit_pct=contract.hard_hit_pct,
            chase_rate=contract.chase_rate,
            whiff_rate=contract.whiff_rate,
            fb_velocity=contract.fb_velocity,
            fb_spin=contract.fb_spin,
            xera=contract.xera,
            k_percent=contract.k_percent,
            bb_percent=contract.bb_percent,
            whiff_percent_pitcher=contract.whiff_percent_pitcher,
            chase_percent_pitcher=contract.chase_percent_pitcher,
        )

        # Run prediction
        result = prediction_service.predict(pred_request)

        # Build response with actual contract data
        return PredictionResponse(
            player_name=contract.player_name,
            position=contract.position,
            predicted_aav=result['predicted_aav'] * 1_000_000,
            predicted_aav_low=result['predicted_aav_low'] * 1_000_000,
            predicted_aav_high=result['predicted_aav_high'] * 1_000_000,
            predicted_length=result['predicted_length'],
            actual_aav=contract.aav,
            actual_length=contract.length,
            signing_war_3yr=contract.war_3yr,
            signing_wrc_plus_3yr=contract.wrc_plus_3yr,
            signing_era_3yr=contract.era_3yr,
            recent_war_3yr=contract.recent_war_3yr,
            recent_wrc_plus_3yr=contract.recent_wrc_plus_3yr,
            recent_era_3yr=contract.recent_era_3yr,
            confidence_score=result['confidence_score'],
            comparables=result['comparables'],
            feature_importance=result['feature_importance'],
            model_accuracy=result['model_accuracy'],
        )

    # Try to find in players table (prospects)
    player = db.query(Player).filter(
        Player.name.ilike(player_name)
    ).first()

    if player:
        # Build prediction request from player data
        age = player.current_age or 25
        pred_request = PredictionRequest(
            name=player.name,
            position=player.position,
            age=age,
            war_3yr=player.war_3yr or 2.0,
            wrc_plus_3yr=player.wrc_plus_3yr,
            avg_3yr=player.avg_3yr,
            obp_3yr=player.obp_3yr,
            slg_3yr=player.slg_3yr,
            hr_3yr=player.hr_3yr,
            era_3yr=player.era_3yr,
            fip_3yr=player.fip_3yr,
            k_9_3yr=player.k_9_3yr,
            bb_9_3yr=player.bb_9_3yr,
            ip_3yr=player.ip_3yr,
            avg_exit_velo=player.avg_exit_velo,
            barrel_rate=player.barrel_rate,
            max_exit_velo=player.max_exit_velo,
            hard_hit_pct=player.hard_hit_pct,
            chase_rate=player.chase_rate,
            whiff_rate=player.whiff_rate,
            fb_velocity=player.fb_velocity,
            fb_spin=player.fb_spin,
            xera=player.xera,
            k_percent=player.k_percent,
            bb_percent=player.bb_percent,
            whiff_percent_pitcher=player.whiff_percent_pitcher,
            chase_percent_pitcher=player.chase_percent_pitcher,
        )

        # Run prediction
        result = prediction_service.predict(pred_request)

        return PredictionResponse(
            player_name=player.name,
            position=player.position,
            predicted_aav=result['predicted_aav'] * 1_000_000,
            predicted_aav_low=result['predicted_aav_low'] * 1_000_000,
            predicted_aav_high=result['predicted_aav_high'] * 1_000_000,
            predicted_length=result['predicted_length'],
            confidence_score=result['confidence_score'],
            comparables=result['comparables'],
            feature_importance=result['feature_importance'],
            model_accuracy=result['model_accuracy'],
        )

    raise ValueError(f"Player not found: {player_name}")


def _build_actions_from_claude(
    claude_actions: list,
    player_name: str
) -> list[ChatAction]:
    """Convert Claude's parsed actions to ChatAction objects."""
    actions = []

    for action in claude_actions:
        action_type_str = action.get("action_type", "")

        try:
            if action_type_str == "view_prediction":
                actions.append(ChatAction(
                    action_type=ChatActionType.VIEW_PREDICTION,
                    target_player=action.get("target_player", player_name)
                ))
            elif action_type_str == "compare_players":
                actions.append(ChatAction(
                    action_type=ChatActionType.COMPARE_PLAYERS,
                    parameters=action.get("parameters", {})
                ))
            elif action_type_str == "show_contracts":
                actions.append(ChatAction(
                    action_type=ChatActionType.SHOW_CONTRACTS,
                    parameters=action.get("parameters", {})
                ))
        except Exception as e:
            logger.warning(f"Failed to parse action {action}: {e}")

    return actions


async def _build_two_way_context(
    player_name: str,
    primary_prediction: PredictionResponse,
    db: Session
) -> tuple[str, list[TwoWayPrediction], float]:
    """
    Build context for a two-way player by running predictions for both roles.

    Args:
        player_name: Player name
        primary_prediction: The initial prediction (usually as DH)
        db: Database session

    Returns:
        Tuple of (context_string, two_way_predictions_list, combined_aav)
    """
    # Get two-way stats
    two_way_stats = context_service.get_two_way_stats(player_name, db)

    # Primary prediction is already run (as DH/batter)
    batter_prediction = {
        'predicted_aav': primary_prediction.predicted_aav / 1_000_000,
        'predicted_length': primary_prediction.predicted_length,
        'confidence_score': primary_prediction.confidence_score
    }

    # Run prediction as pitcher if we have pitching stats
    pitcher_prediction = {'predicted_aav': 0, 'predicted_length': 0, 'confidence_score': 0}

    if two_way_stats.get('pitching'):
        pitching = two_way_stats['pitching']
        try:
            # Create a pitcher prediction request
            # Get age from contract data - Ohtani was 29 at signing
            pred_request = PredictionRequest(
                name=player_name,
                position="SP",  # Assume starting pitcher
                age=29,  # Default age for two-way players (can be improved later)
                war_3yr=pitching.get('war_3yr', 3.0),
                era_3yr=pitching.get('era_3yr', 3.5),
                ip_3yr=pitching.get('ip_3yr', 150.0),
            )

            result = prediction_service.predict(pred_request)
            pitcher_prediction = {
                'predicted_aav': result['predicted_aav'],
                'predicted_length': result['predicted_length'],
                'confidence_score': result['confidence_score']
            }
        except Exception as e:
            logger.warning(f"Failed to get pitcher prediction for {player_name}: {e}")
            # Fall back to estimated pitching value based on WAR
            if pitching.get('war_3yr'):
                # Rough estimate: ~$8M per WAR for pitchers
                pitcher_prediction['predicted_aav'] = pitching['war_3yr'] * 8
                pitcher_prediction['confidence_score'] = 50

    # Build the two-way context string
    context = context_service.build_two_way_context(
        player_name=player_name,
        batter_prediction=batter_prediction,
        pitcher_prediction=pitcher_prediction,
        actual_aav=primary_prediction.actual_aav,
        actual_length=primary_prediction.actual_length
    )

    # Build TwoWayPrediction objects for API response
    two_way_predictions = [
        TwoWayPrediction(
            role="DH",
            predicted_aav=batter_prediction['predicted_aav'],
            predicted_length=batter_prediction['predicted_length'],
            confidence_score=batter_prediction['confidence_score']
        ),
        TwoWayPrediction(
            role="SP",
            predicted_aav=pitcher_prediction['predicted_aav'],
            predicted_length=pitcher_prediction['predicted_length'],
            confidence_score=pitcher_prediction['confidence_score']
        )
    ]

    combined_aav = batter_prediction['predicted_aav'] + pitcher_prediction['predicted_aav']

    return context, two_way_predictions, combined_aav

"""
Pydantic schemas for request/response validation.
"""
from enum import Enum
from typing import Optional, List
from pydantic import BaseModel, Field


# ============================================================================
# Prediction Schemas
# ============================================================================

class PredictionRequest(BaseModel):
    """Request body for contract prediction."""
    name: str = Field(..., description="Player name")
    position: str = Field(..., description="Position (e.g., SS, SP, RF)")
    age: int = Field(..., ge=18, le=50, description="Age at signing")

    # Required stats
    war_3yr: float = Field(..., description="3-year average WAR")

    # Batter stats (required for non-pitchers)
    wrc_plus_3yr: Optional[float] = Field(None, description="3-year average wRC+")
    avg_3yr: Optional[float] = Field(None, description="3-year batting average")
    obp_3yr: Optional[float] = Field(None, description="3-year OBP")
    slg_3yr: Optional[float] = Field(None, description="3-year SLG")
    hr_3yr: Optional[float] = Field(None, description="3-year average HR")

    # Pitcher stats (required for pitchers)
    era_3yr: Optional[float] = Field(None, description="3-year average ERA")
    fip_3yr: Optional[float] = Field(None, description="3-year average FIP")
    k_9_3yr: Optional[float] = Field(None, description="3-year K/9")
    bb_9_3yr: Optional[float] = Field(None, description="3-year BB/9")
    ip_3yr: Optional[float] = Field(None, description="3-year average IP")

    # Optional Statcast metrics (batters only)
    avg_exit_velo: Optional[float] = Field(None, description="Average exit velocity")
    barrel_rate: Optional[float] = Field(None, description="Barrel rate %")
    max_exit_velo: Optional[float] = Field(None, description="Max exit velocity")
    hard_hit_pct: Optional[float] = Field(None, description="Hard hit %")

    # Plate discipline metrics (percentiles 0-100, batters only)
    chase_rate: Optional[float] = Field(None, description="Chase rate percentile (0-100)")
    whiff_rate: Optional[float] = Field(None, description="Whiff rate percentile (0-100)")

    # Pitcher Statcast metrics (percentiles 0-100, pitchers only)
    fb_velocity: Optional[float] = Field(None, description="Fastball velocity percentile (0-100)")
    fb_spin: Optional[float] = Field(None, description="Fastball spin percentile (0-100)")
    xera: Optional[float] = Field(None, description="Expected ERA percentile (0-100)")
    k_percent: Optional[float] = Field(None, description="K% percentile (0-100)")
    bb_percent: Optional[float] = Field(None, description="BB% percentile (0-100)")
    whiff_percent_pitcher: Optional[float] = Field(None, description="Whiff% induced percentile (0-100)")
    chase_percent_pitcher: Optional[float] = Field(None, description="Chase% induced percentile (0-100)")

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Juan Soto",
                "position": "RF",
                "age": 26,
                "war_3yr": 6.1,
                "wrc_plus_3yr": 160,
                "avg_3yr": 0.268,
                "obp_3yr": 0.410,
                "slg_3yr": 0.513,
                "hr_3yr": 34,
                "avg_exit_velo": 94.2,
                "barrel_rate": 19.7,
                "max_exit_velo": 115.7,
                "hard_hit_pct": 57.0
            }
        }


class ComparablePlayer(BaseModel):
    """A comparable player from historical data."""
    name: str
    position: str
    signing_team: Optional[str] = Field(None, description="Team that signed the player")
    year_signed: int
    age_at_signing: int
    aav: float
    length: int
    war_3yr: float
    similarity_score: float = Field(..., ge=0, le=100)
    is_extension: bool = Field(False, description="True if this was a pre-FA extension")


class PredictionResponse(BaseModel):
    """Response for contract prediction."""
    player_name: str
    position: str
    signing_team: Optional[str] = Field(None, description="Team that signed the player (if contract exists)")

    # Predictions
    predicted_aav: float = Field(..., description="Predicted AAV in dollars")
    predicted_aav_low: float = Field(..., description="Low estimate (AAV - MAE)")
    predicted_aav_high: float = Field(..., description="High estimate (AAV + MAE)")
    predicted_length: float = Field(..., description="Predicted contract length in years")

    # Actual contract (for signed players only)
    actual_aav: Optional[float] = Field(None, description="Actual AAV if player has signed contract")
    actual_length: Optional[int] = Field(None, description="Actual contract length if signed")

    # Stats at signing (3 years prior to contract)
    signing_war_3yr: Optional[float] = Field(None, description="WAR at time of signing")
    signing_wrc_plus_3yr: Optional[float] = Field(None, description="wRC+ at time of signing")
    signing_era_3yr: Optional[float] = Field(None, description="ERA at time of signing (pitchers)")

    # Recent performance stats (last 3 years from current date)
    recent_war_3yr: Optional[float] = Field(None, description="Recent 3-year WAR")
    recent_wrc_plus_3yr: Optional[float] = Field(None, description="Recent 3-year wRC+")
    recent_era_3yr: Optional[float] = Field(None, description="Recent 3-year ERA (pitchers)")

    # Prediction based on recent performance (for contract assessment)
    predicted_aav_recent: Optional[float] = Field(None, description="Predicted AAV based on recent performance")

    # Confidence
    confidence_score: float = Field(..., ge=0, le=100, description="Model confidence %")

    # Comparables (based on stats at time of signing)
    comparables: List[ComparablePlayer] = Field(default_factory=list)

    # Comparables based on recent performance
    comparables_recent: List[ComparablePlayer] = Field(default_factory=list)

    # Feature importance (top 5)
    feature_importance: dict = Field(default_factory=dict)

    # Model info
    model_accuracy: float = Field(..., description="Model accuracy within $5M")


# ============================================================================
# Player Search Schemas
# ============================================================================

class PlayerStats(BaseModel):
    """Player stats for auto-fill."""
    # Basic info
    name: str
    position: str

    # For signed players (from Contract table)
    age_at_signing: Optional[int] = None
    year_signed: Optional[int] = None

    # For prospects (from Player table)
    current_age: Optional[int] = None
    last_season: Optional[int] = None

    # Core stats
    war_3yr: Optional[float] = None

    # Batter stats
    wrc_plus_3yr: Optional[float] = None
    avg_3yr: Optional[float] = None
    obp_3yr: Optional[float] = None
    slg_3yr: Optional[float] = None
    hr_3yr: Optional[float] = None

    # Pitcher stats
    era_3yr: Optional[float] = None
    fip_3yr: Optional[float] = None
    k_9_3yr: Optional[float] = None
    bb_9_3yr: Optional[float] = None
    ip_3yr: Optional[float] = None

    # Statcast
    avg_exit_velo: Optional[float] = None
    barrel_rate: Optional[float] = None
    max_exit_velo: Optional[float] = None
    hard_hit_pct: Optional[float] = None

    # Plate discipline (percentiles 0-100, batters)
    chase_rate: Optional[float] = None
    whiff_rate: Optional[float] = None

    # Pitcher Statcast (percentiles 0-100)
    fb_velocity: Optional[float] = None
    fb_spin: Optional[float] = None
    xera: Optional[float] = None
    k_percent: Optional[float] = None
    bb_percent: Optional[float] = None
    whiff_percent_pitcher: Optional[float] = None
    chase_percent_pitcher: Optional[float] = None

    class Config:
        from_attributes = True


class PlayerSearchResult(BaseModel):
    """Player search result for autocomplete."""
    id: int
    name: str
    position: str
    team: Optional[str] = None
    is_pitcher: bool = False
    has_contract: bool = False
    stats: Optional[PlayerStats] = None


class PlayerSearchResponse(BaseModel):
    """Response for player search."""
    results: List[PlayerSearchResult]
    count: int


# ============================================================================
# Contract Database Schemas
# ============================================================================

class ContractRecord(BaseModel):
    """Historical contract record."""
    id: int
    player_name: str
    position: str
    year_signed: int
    age_at_signing: int
    aav: float
    total_value: float
    length: int
    war_3yr: Optional[float] = None
    is_extension: bool = False

    class Config:
        from_attributes = True


class ContractListResponse(BaseModel):
    """Paginated contract list response."""
    contracts: List[ContractRecord]
    total: int
    page: int
    per_page: int
    total_pages: int


# ============================================================================
# Year-by-Year Stats Schemas
# ============================================================================

class BatterYearlyStats(BaseModel):
    """Single season batting stats."""
    season: int
    team: str
    war: Optional[float] = None
    wrc_plus: Optional[float] = None
    avg: Optional[float] = None
    obp: Optional[float] = None
    slg: Optional[float] = None
    hr: Optional[int] = None
    rbi: Optional[int] = None
    sb: Optional[int] = None
    runs: Optional[int] = None
    hits: Optional[int] = None
    games: Optional[int] = None
    pa: Optional[int] = None


class PitcherYearlyStats(BaseModel):
    """Single season pitching stats."""
    season: int
    team: str
    war: Optional[float] = None
    era: Optional[float] = None
    fip: Optional[float] = None
    k_9: Optional[float] = None
    bb_9: Optional[float] = None
    ip: Optional[float] = None
    games: Optional[int] = None
    wins: Optional[int] = None
    losses: Optional[int] = None


class PlayerYearlyStatsResponse(BaseModel):
    """Response for player year-by-year stats."""
    player_name: str
    position: str
    is_pitcher: bool
    seasons: List[int] = Field(default_factory=list, description="Years included in response")
    batter_stats: Optional[List[BatterYearlyStats]] = None
    pitcher_stats: Optional[List[PitcherYearlyStats]] = None


class ContractSummaryResponse(BaseModel):
    """Summary statistics for the contracts database."""
    total_contracts: int
    year_min: int
    year_max: int
    aav_min: float
    aav_max: float
    unique_positions: int


# ============================================================================
# Health Check
# ============================================================================

class HealthResponse(BaseModel):
    """API health check response."""
    status: str = "ok"
    version: str
    models_loaded: bool
    database_connected: bool


# ============================================================================
# Chat / Natural Language Query Schemas
# ============================================================================

class ChatActionType(str, Enum):
    """Types of actions that can be suggested in chat responses."""
    VIEW_PREDICTION = "view_prediction"
    COMPARE_PLAYERS = "compare_players"
    SHOW_CONTRACTS = "show_contracts"


class ChatAction(BaseModel):
    """An action button suggested in a chat response."""
    action_type: ChatActionType
    target_player: Optional[str] = None
    parameters: dict = Field(default_factory=dict)


class ChatRequest(BaseModel):
    """Request body for chat/natural language query."""
    query: str = Field(
        ...,
        min_length=3,
        max_length=500,
        description="Natural language query about a player or contract"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "query": "What would Juan Soto be worth?"
            }
        }


class TwoWayPrediction(BaseModel):
    """Prediction summary for a two-way player role."""
    role: str = Field(..., description="Role (e.g., 'DH' or 'SP')")
    predicted_aav: float = Field(..., description="Predicted AAV in millions")
    predicted_length: float = Field(..., description="Predicted contract length")
    confidence_score: float = Field(..., description="Confidence score 0-100")


class ChatResponse(BaseModel):
    """Response for chat/natural language query."""
    response: str = Field(..., description="Claude's explanation of the prediction")
    prediction: Optional[PredictionResponse] = Field(
        None,
        description="Full prediction if a player was identified"
    )
    actions: List[ChatAction] = Field(
        default_factory=list,
        description="Suggested action buttons"
    )

    # Status fields
    player_found: bool = Field(..., description="Whether a player was identified in the query")
    player_name: Optional[str] = Field(None, description="Name of identified player")
    suggestions: List[str] = Field(
        default_factory=list,
        description="Alternative player suggestions if ambiguous"
    )

    # Two-way player fields
    is_two_way_player: bool = Field(False, description="Whether player is a two-way player")
    two_way_predictions: Optional[List[TwoWayPrediction]] = Field(
        None,
        description="Separate predictions for each role (batting/pitching)"
    )
    combined_aav: Optional[float] = Field(
        None,
        description="Combined AAV for two-way players in millions"
    )

    # Claude availability
    claude_available: bool = Field(True, description="Whether Claude API responded")
    used_fallback: bool = Field(False, description="Whether fallback template was used")

"""
Pydantic schemas for request/response validation.
"""
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

    # Confidence
    confidence_score: float = Field(..., ge=0, le=100, description="Model confidence %")

    # Comparables
    comparables: List[ComparablePlayer] = Field(default_factory=list)

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
# Health Check
# ============================================================================

class HealthResponse(BaseModel):
    """API health check response."""
    status: str = "ok"
    version: str
    models_loaded: bool
    database_connected: bool

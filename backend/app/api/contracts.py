"""
Contract database API endpoints.
"""
from typing import Optional, List
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc, asc
import math

from app.models.database import get_db, Contract
from sqlalchemy import func
from app.models.schemas import (
    ContractListResponse,
    ContractRecord,
    ContractSummaryResponse,
    PlayerYearlyStatsResponse,
    BatterYearlyStats,
    PitcherYearlyStats,
)
from app.services.stats_service import stats_service

router = APIRouter(prefix="/contracts", tags=["Contracts"])


@router.get("", response_model=ContractListResponse)
async def list_contracts(
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Results per page"),
    position: Optional[str] = Query(None, description="Filter by position"),
    year_min: Optional[int] = Query(None, description="Minimum year signed"),
    year_max: Optional[int] = Query(None, description="Maximum year signed"),
    aav_min: Optional[float] = Query(None, description="Minimum AAV in millions"),
    aav_max: Optional[float] = Query(None, description="Maximum AAV in millions"),
    war_min: Optional[float] = Query(None, description="Minimum 3-year WAR"),
    war_max: Optional[float] = Query(None, description="Maximum 3-year WAR"),
    length_min: Optional[int] = Query(None, description="Minimum contract length"),
    length_max: Optional[int] = Query(None, description="Maximum contract length"),
    team: Optional[str] = Query(None, description="Filter by team"),
    sort_by: str = Query("aav", description="Sort field: aav, year, name, length"),
    sort_order: str = Query("desc", description="Sort order: asc or desc"),
    search: Optional[str] = Query(None, description="Search by player name"),
    db: Session = Depends(get_db)
):
    """
    Search and filter historical contracts.

    Features:
    - Pagination (20 per page default)
    - Filter by position, year range, AAV range, WAR range, length range, team
    - Sort by AAV, year, name, length
    - Search by player name
    """
    query = db.query(Contract)

    # Apply filters
    if position:
        query = query.filter(Contract.position == position.upper())

    if year_min:
        query = query.filter(Contract.year_signed >= year_min)

    if year_max:
        query = query.filter(Contract.year_signed <= year_max)

    # AAV filters (convert millions to actual value)
    if aav_min is not None:
        query = query.filter(Contract.aav >= aav_min * 1_000_000)

    if aav_max is not None:
        query = query.filter(Contract.aav <= aav_max * 1_000_000)

    # WAR filters
    if war_min is not None:
        query = query.filter(Contract.war_3yr >= war_min)

    if war_max is not None:
        query = query.filter(Contract.war_3yr <= war_max)

    # Length filters
    if length_min is not None:
        query = query.filter(Contract.length >= length_min)

    if length_max is not None:
        query = query.filter(Contract.length <= length_max)

    if search:
        query = query.filter(Contract.player_name.ilike(f"%{search}%"))

    # Get total count before pagination
    total = query.count()

    # Apply sorting
    sort_column = {
        'aav': Contract.aav,
        'year': Contract.year_signed,
        'name': Contract.player_name,
        'length': Contract.length,
    }.get(sort_by, Contract.aav)

    if sort_order.lower() == 'asc':
        query = query.order_by(asc(sort_column))
    else:
        query = query.order_by(desc(sort_column))

    # Apply pagination
    offset = (page - 1) * per_page
    contracts = query.offset(offset).limit(per_page).all()

    # Calculate total pages
    total_pages = math.ceil(total / per_page) if total > 0 else 1

    return ContractListResponse(
        contracts=[ContractRecord.model_validate(c) for c in contracts],
        total=total,
        page=page,
        per_page=per_page,
        total_pages=total_pages
    )


@router.get("/summary", response_model=ContractSummaryResponse)
async def get_contracts_summary(db: Session = Depends(get_db)):
    """Get summary statistics for the contracts database."""
    result = db.query(
        func.count(Contract.id).label('total'),
        func.min(Contract.year_signed).label('year_min'),
        func.max(Contract.year_signed).label('year_max'),
        func.min(Contract.aav).label('aav_min'),
        func.max(Contract.aav).label('aav_max'),
        func.count(func.distinct(Contract.position)).label('positions')
    ).first()

    return ContractSummaryResponse(
        total_contracts=result.total,
        year_min=result.year_min,
        year_max=result.year_max,
        aav_min=result.aav_min,
        aav_max=result.aav_max,
        unique_positions=result.positions
    )


@router.get("/{contract_id}", response_model=ContractRecord)
async def get_contract(
    contract_id: int,
    db: Session = Depends(get_db)
):
    """Get a single contract by ID."""
    contract = db.query(Contract).filter(Contract.id == contract_id).first()

    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")

    return ContractRecord.model_validate(contract)


# Pitcher positions for determining player type
PITCHER_POSITIONS = ['SP', 'RP', 'P', 'CL']


@router.get("/{contract_id}/stats", response_model=PlayerYearlyStatsResponse)
async def get_contract_player_stats(
    contract_id: int,
    num_years: int = Query(3, ge=1, le=10, description="Number of recent seasons to include"),
    db: Session = Depends(get_db)
):
    """
    Get year-by-year stats for the player associated with a contract.

    Returns individual season stats for the most recent completed seasons.
    The years are dynamically determined based on the current date.
    """
    # Get the contract
    contract = db.query(Contract).filter(Contract.id == contract_id).first()
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")

    # Check if stats service is loaded
    if not stats_service.is_loaded:
        raise HTTPException(
            status_code=503,
            detail="Stats data not available. FanGraphs CSV files may not be loaded."
        )

    # Determine if pitcher
    is_pitcher = contract.position.upper() in PITCHER_POSITIONS

    # Get the seasons that will be queried
    seasons = stats_service.get_recent_completed_seasons(num_years)

    # Get yearly stats
    stats = stats_service.get_player_yearly_stats(
        player_name=contract.player_name,
        is_pitcher=is_pitcher,
        num_years=num_years
    )

    if is_pitcher:
        return PlayerYearlyStatsResponse(
            player_name=contract.player_name,
            position=contract.position,
            is_pitcher=True,
            seasons=seasons,
            pitcher_stats=[PitcherYearlyStats(**s) for s in stats],
            batter_stats=None
        )
    else:
        return PlayerYearlyStatsResponse(
            player_name=contract.player_name,
            position=contract.position,
            is_pitcher=False,
            seasons=seasons,
            batter_stats=[BatterYearlyStats(**s) for s in stats],
            pitcher_stats=None
        )

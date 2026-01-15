"""
Player search API endpoints.
"""
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.models.database import get_db, Player, Contract
from app.models.schemas import PlayerSearchResponse, PlayerSearchResult, PlayerStats

router = APIRouter(prefix="/players", tags=["Players"])


@router.get("/search", response_model=PlayerSearchResponse)
async def search_players(
    q: str = Query(..., min_length=2, description="Search query (min 2 characters)"),
    limit: int = Query(10, ge=1, le=50, description="Max results to return"),
    include_stats: bool = Query(True, description="Include player stats from most recent contract"),
    db: Session = Depends(get_db)
):
    """
    Search for players by name with autocomplete.

    - Triggers after 2 characters
    - Returns player name, position, team
    - Optionally includes 3-year average stats from most recent contract
    - Response time target: < 300ms
    """
    # Search by name (case-insensitive)
    query = db.query(Player).filter(
        Player.name.ilike(f"%{q}%")
    ).limit(limit)

    players = query.all()

    results = []
    for p in players:
        stats = None

        if include_stats:
            # Get the most recent contract for this player
            contract = db.query(Contract).filter(
                Contract.player_name == p.name
            ).order_by(desc(Contract.year_signed)).first()

            if contract:
                stats = PlayerStats(
                    name=contract.player_name,
                    position=contract.position,
                    age_at_signing=contract.age_at_signing,
                    year_signed=contract.year_signed,
                    war_3yr=contract.war_3yr,
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
                )

        results.append(PlayerSearchResult(
            id=p.id,
            name=p.name,
            position=p.position,
            team=p.team,
            is_pitcher=p.is_pitcher,
            stats=stats
        ))

    return PlayerSearchResponse(
        results=results,
        count=len(results)
    )

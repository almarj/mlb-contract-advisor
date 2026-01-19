"""
Player search API endpoints.
"""
import logging
from typing import Optional, Dict
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.models.database import get_db, Player, Contract
from app.models.schemas import PlayerSearchResponse, PlayerSearchResult, PlayerStats

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/players", tags=["Players"])


@router.get("/search", response_model=PlayerSearchResponse)
async def search_players(
    q: str = Query(..., min_length=2, description="Search query (min 2 characters)"),
    limit: int = Query(10, ge=1, le=50, description="Max results to return"),
    include_stats: bool = Query(True, description="Include player stats"),
    player_type: Optional[str] = Query(None, description="Filter: 'signed', 'prospect', or None for both"),
    db: Session = Depends(get_db)
):
    """
    Search for players by name with autocomplete.

    Returns both signed players (historical contracts) and prospects (FanGraphs data).

    - Triggers after 2 characters
    - Returns player name, position, team, has_contract flag
    - Optionally includes 3-year average stats
    - Signed players first, then prospects
    - Response time target: < 300ms
    """
    # Build query
    query = db.query(Player).filter(Player.name.ilike(f"%{q}%"))

    # Optional filter by player type
    if player_type == "signed":
        query = query.filter(Player.has_contract == True)
    elif player_type == "prospect":
        query = query.filter(Player.has_contract == False)

    # Order: signed players first, then by name
    query = query.order_by(desc(Player.has_contract), Player.name).limit(limit)

    players = query.all()

    # Batch load contracts for signed players to avoid N+1 queries
    contracts_map: Dict[str, Contract] = {}
    if include_stats:
        signed_player_names = [p.name for p in players if p.has_contract]
        if signed_player_names:
            # Get all contracts for matching players in ONE query
            contracts = db.query(Contract).filter(
                Contract.player_name.in_(signed_player_names)
            ).order_by(desc(Contract.year_signed)).all()

            # Keep only the most recent contract per player
            for contract in contracts:
                if contract.player_name not in contracts_map:
                    contracts_map[contract.player_name] = contract

    results = []
    for p in players:
        stats = None

        if include_stats:
            if p.has_contract:
                # Signed player: get stats from pre-loaded contracts map
                contract = contracts_map.get(p.name)

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
                        # Batter Statcast
                        avg_exit_velo=contract.avg_exit_velo,
                        barrel_rate=contract.barrel_rate,
                        max_exit_velo=contract.max_exit_velo,
                        hard_hit_pct=contract.hard_hit_pct,
                        chase_rate=contract.chase_rate,
                        whiff_rate=contract.whiff_rate,
                        # Pitcher Statcast
                        fb_velocity=contract.fb_velocity,
                        fb_spin=contract.fb_spin,
                        xera=contract.xera,
                        k_percent=contract.k_percent,
                        bb_percent=contract.bb_percent,
                        whiff_percent_pitcher=contract.whiff_percent_pitcher,
                        chase_percent_pitcher=contract.chase_percent_pitcher,
                    )
            else:
                # Prospect: get stats directly from Player table
                stats = PlayerStats(
                    name=p.name,
                    position=p.position,
                    current_age=p.current_age,
                    last_season=p.last_season,
                    war_3yr=p.war_3yr,
                    wrc_plus_3yr=p.wrc_plus_3yr,
                    avg_3yr=p.avg_3yr,
                    obp_3yr=p.obp_3yr,
                    slg_3yr=p.slg_3yr,
                    hr_3yr=p.hr_3yr,
                    era_3yr=p.era_3yr,
                    fip_3yr=p.fip_3yr,
                    k_9_3yr=p.k_9_3yr,
                    bb_9_3yr=p.bb_9_3yr,
                    ip_3yr=p.ip_3yr,
                    # Batter Statcast
                    avg_exit_velo=p.avg_exit_velo,
                    barrel_rate=p.barrel_rate,
                    max_exit_velo=p.max_exit_velo,
                    hard_hit_pct=p.hard_hit_pct,
                    chase_rate=p.chase_rate,
                    whiff_rate=p.whiff_rate,
                    # Pitcher Statcast
                    fb_velocity=p.fb_velocity,
                    fb_spin=p.fb_spin,
                    xera=p.xera,
                    k_percent=p.k_percent,
                    bb_percent=p.bb_percent,
                    whiff_percent_pitcher=p.whiff_percent_pitcher,
                    chase_percent_pitcher=p.chase_percent_pitcher,
                )

        results.append(PlayerSearchResult(
            id=p.id,
            name=p.name,
            position=p.position,
            team=p.team,
            is_pitcher=p.is_pitcher,
            has_contract=p.has_contract,
            stats=stats
        ))

    return PlayerSearchResponse(
        results=results,
        count=len(results)
    )

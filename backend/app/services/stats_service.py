"""
Stats service for fetching year-by-year player stats.

Uses pre-computed data from the database for fast lookups (<50ms).
Falls back to pybaseball API calls if database has no data.
"""
import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict, Optional

from sqlalchemy.orm import Session

from app.utils import normalize_name, get_recent_completed_seasons

logger = logging.getLogger(__name__)

# Thread pool for fallback pybaseball calls (if needed)
_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="stats_fallback")


class StatsService:
    """Service to fetch and query year-by-year player stats."""

    def __init__(self):
        self._loaded = True

    def get_recent_completed_seasons(self, num_years: int = 3) -> List[int]:
        """
        Dynamically determine the last N completed MLB seasons.
        """
        return get_recent_completed_seasons(num_years)

    def get_player_yearly_stats_from_db(
        self,
        db: Session,
        player_name: str,
        is_pitcher: bool,
        num_years: int = 3
    ) -> List[Dict]:
        """
        Get year-by-year stats from the database (fast path).

        Args:
            db: Database session
            player_name: Name of the player to look up
            is_pitcher: True for pitcher stats, False for batter stats
            num_years: Number of recent seasons to return (default 3)

        Returns:
            List of dicts containing stats for each season found
        """
        from app.models.database import PlayerYearlyStats

        # Get the years to query
        years = self.get_recent_completed_seasons(num_years)

        # Normalize search name for lookup
        search_name = normalize_name(player_name)

        # Query database
        stats = db.query(PlayerYearlyStats).filter(
            PlayerYearlyStats.normalized_name == search_name,
            PlayerYearlyStats.is_pitcher == is_pitcher,
            PlayerYearlyStats.season.in_(years)
        ).order_by(PlayerYearlyStats.season).all()

        results = []
        for s in stats:
            if is_pitcher:
                results.append({
                    'season': s.season,
                    'team': s.team or '',
                    'war': s.war,
                    'era': s.era,
                    'fip': s.fip,
                    'k_9': s.k_9,
                    'bb_9': s.bb_9,
                    'ip': s.ip,
                    'games': s.games,
                    'wins': s.wins,
                    'losses': s.losses,
                })
            else:
                results.append({
                    'season': s.season,
                    'team': s.team or '',
                    'war': s.war,
                    'wrc_plus': s.wrc_plus,
                    'avg': s.avg,
                    'obp': s.obp,
                    'slg': s.slg,
                    'hr': s.hr,
                    'rbi': s.rbi,
                    'sb': s.sb,
                    'runs': s.runs,
                    'hits': s.hits,
                    'games': s.games,
                    'pa': s.pa,
                })

        return results

    def get_player_yearly_stats(
        self,
        player_name: str,
        is_pitcher: bool,
        num_years: int = 3
    ) -> List[Dict]:
        """
        Get year-by-year stats using pybaseball (fallback/legacy method).

        This method makes live API calls and is slow (5-10 seconds).
        Prefer get_player_yearly_stats_from_db() for fast lookups.
        """
        try:
            from pybaseball import batting_stats, pitching_stats, cache
            cache.enable()
        except ImportError:
            logger.warning("pybaseball not available for fallback stats fetch")
            return []

        years = self.get_recent_completed_seasons(num_years)
        start_year = min(years)
        end_year = max(years)
        search_name = normalize_name(player_name)

        results = []

        try:
            if is_pitcher:
                df = pitching_stats(start_year, end_year, qual=1)
                if df is None or df.empty:
                    return []

                df['name_normalized'] = df['Name'].apply(normalize_name)
                matches = df[df['name_normalized'] == search_name].sort_values('Season')

                for _, row in matches.iterrows():
                    results.append({
                        'season': int(row['Season']),
                        'team': str(row.get('Team', '')),
                        'war': float(row['WAR']) if 'WAR' in row and row['WAR'] is not None else None,
                        'era': float(row['ERA']) if 'ERA' in row and row['ERA'] is not None else None,
                        'fip': float(row['FIP']) if 'FIP' in row and row['FIP'] is not None else None,
                        'k_9': float(row['K/9']) if 'K/9' in row and row['K/9'] is not None else None,
                        'bb_9': float(row['BB/9']) if 'BB/9' in row and row['BB/9'] is not None else None,
                        'ip': float(row['IP']) if 'IP' in row and row['IP'] is not None else None,
                        'games': int(row['G']) if 'G' in row and row['G'] is not None else None,
                        'wins': int(row['W']) if 'W' in row and row['W'] is not None else None,
                        'losses': int(row['L']) if 'L' in row and row['L'] is not None else None,
                    })
            else:
                df = batting_stats(start_year, end_year, qual=1)
                if df is None or df.empty:
                    return []

                df['name_normalized'] = df['Name'].apply(normalize_name)
                matches = df[df['name_normalized'] == search_name].sort_values('Season')

                for _, row in matches.iterrows():
                    results.append({
                        'season': int(row['Season']),
                        'team': str(row.get('Team', '')),
                        'war': float(row['WAR']) if 'WAR' in row and row['WAR'] is not None else None,
                        'wrc_plus': float(row['wRC+']) if 'wRC+' in row and row['wRC+'] is not None else None,
                        'avg': float(row['AVG']) if 'AVG' in row and row['AVG'] is not None else None,
                        'obp': float(row['OBP']) if 'OBP' in row and row['OBP'] is not None else None,
                        'slg': float(row['SLG']) if 'SLG' in row and row['SLG'] is not None else None,
                        'hr': int(row['HR']) if 'HR' in row and row['HR'] is not None else None,
                        'rbi': int(row['RBI']) if 'RBI' in row and row['RBI'] is not None else None,
                        'sb': int(row['SB']) if 'SB' in row and row['SB'] is not None else None,
                        'runs': int(row['R']) if 'R' in row and row['R'] is not None else None,
                        'hits': int(row['H']) if 'H' in row and row['H'] is not None else None,
                        'games': int(row['G']) if 'G' in row and row['G'] is not None else None,
                        'pa': int(row['PA']) if 'PA' in row and row['PA'] is not None else None,
                    })
        except Exception as e:
            logger.exception("Error fetching stats for %s: %s", player_name, e)
            return []

        return results

    async def get_player_yearly_stats_async(
        self,
        db: Optional[Session],
        player_name: str,
        is_pitcher: bool,
        num_years: int = 3
    ) -> List[Dict]:
        """
        Async method to get player stats.

        Tries database first (fast), falls back to pybaseball if no results.

        Args:
            db: Database session (if available)
            player_name: Name of the player to look up
            is_pitcher: True for pitcher stats, False for batter stats
            num_years: Number of recent seasons to return (default 3)

        Returns:
            List of dicts containing stats for each season found
        """
        # Try database first (fast path)
        if db is not None:
            results = self.get_player_yearly_stats_from_db(
                db, player_name, is_pitcher, num_years
            )
            if results:
                logger.debug("Found %d seasons for %s in database", len(results), player_name)
                return results

        # Fall back to pybaseball (slow path)
        logger.info("No database stats for %s, falling back to pybaseball", player_name)
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            _executor,
            self.get_player_yearly_stats,
            player_name,
            is_pitcher,
            num_years
        )

    @property
    def is_loaded(self) -> bool:
        """Check if service is ready."""
        return self._loaded


# Singleton instance for use across the application
stats_service = StatsService()

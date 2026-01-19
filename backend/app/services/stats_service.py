"""
Stats service for fetching year-by-year player stats from FanGraphs via pybaseball.
"""
from typing import Optional, List, Dict
from datetime import datetime
import unicodedata
import re

# pybaseball imports
from pybaseball import batting_stats, pitching_stats, cache


# Enable pybaseball caching to avoid repeated API calls
cache.enable()


class StatsService:
    """Service to fetch and query FanGraphs data for year-by-year stats."""

    # MLB season typically ends in early October
    SEASON_END_MONTH = 10

    def __init__(self):
        self._loaded = True  # Always ready since we fetch on-demand

    @staticmethod
    def normalize_name(name: str) -> str:
        """Normalize player name for matching (handles accents, suffixes)."""
        # Remove accents
        normalized = unicodedata.normalize('NFD', name)
        normalized = ''.join(c for c in normalized if unicodedata.category(c) != 'Mn')
        # Remove common suffixes
        normalized = re.sub(r'\s+(jr\.?|sr\.?|ii|iii|iv)$', '', normalized, flags=re.IGNORECASE)
        return normalized.lower().strip()

    def get_recent_completed_seasons(self, num_years: int = 3) -> List[int]:
        """
        Dynamically determine the last N completed MLB seasons.

        MLB season typically ends in early October, so:
        - If current month >= October, current year is complete
        - Otherwise, last complete season is previous year
        """
        now = datetime.now()
        current_year = now.year
        current_month = now.month

        # Determine the most recent completed season
        if current_month >= self.SEASON_END_MONTH:
            last_complete_season = current_year
        else:
            last_complete_season = current_year - 1

        # Return the last N seasons
        return list(range(last_complete_season - num_years + 1, last_complete_season + 1))

    def get_player_yearly_stats(
        self,
        player_name: str,
        is_pitcher: bool,
        num_years: int = 3
    ) -> List[Dict]:
        """
        Get year-by-year stats for a player by fetching from FanGraphs via pybaseball.

        Args:
            player_name: Name of the player to look up
            is_pitcher: True for pitcher stats, False for batter stats
            num_years: Number of recent seasons to return (default 3)

        Returns:
            List of dicts containing stats for each season found
        """
        # Get the years to query
        years = self.get_recent_completed_seasons(num_years)
        start_year = min(years)
        end_year = max(years)

        # Normalize search name
        search_name = self.normalize_name(player_name)

        results = []

        try:
            if is_pitcher:
                # Fetch pitching stats for the year range
                # qual=1 to get all pitchers with at least 1 IP
                df = pitching_stats(start_year, end_year, qual=1)

                if df is None or df.empty:
                    return []

                # Normalize names in dataframe for matching
                df['name_normalized'] = df['Name'].apply(self.normalize_name)

                # Filter by player name
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
                # Fetch batting stats for the year range
                # qual=1 to get all batters with at least 1 PA
                df = batting_stats(start_year, end_year, qual=1)

                if df is None or df.empty:
                    return []

                # Normalize names in dataframe for matching
                df['name_normalized'] = df['Name'].apply(self.normalize_name)

                # Filter by player name
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
            print(f"Error fetching stats for {player_name}: {e}")
            return []

        return results

    @property
    def is_loaded(self) -> bool:
        """Check if service is ready (always True for on-demand fetching)."""
        return self._loaded


# Singleton instance for use across the application
stats_service = StatsService()

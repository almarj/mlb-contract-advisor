"""
Stats service for loading year-by-year player stats from FanGraphs CSV files.
"""
import pandas as pd
from pathlib import Path
from typing import Optional, List, Dict
from datetime import datetime
import unicodedata
import re


class StatsService:
    """Service to load and query FanGraphs CSV data for year-by-year stats."""
    
    # MLB season typically ends in early October
    SEASON_END_MONTH = 10
    
    def __init__(self):
        self.batting_df: Optional[pd.DataFrame] = None
        self.pitching_df: Optional[pd.DataFrame] = None
        self._loaded = False
    
    def load_data(self, data_dir: Path) -> bool:
        """Load FanGraphs CSV data from the specified directory."""
        try:
            batting_path = data_dir / "fangraphs_batting_2015-2025.csv"
            pitching_path = data_dir / "fangraphs_pitching_2015-2025.csv"
            
            if batting_path.exists():
                self.batting_df = pd.read_csv(batting_path)
                print(f"Loaded batting data: {len(self.batting_df)} rows")
            else:
                print(f"Warning: Batting data not found at {batting_path}")
                
            if pitching_path.exists():
                self.pitching_df = pd.read_csv(pitching_path)
                print(f"Loaded pitching data: {len(self.pitching_df)} rows")
            else:
                print(f"Warning: Pitching data not found at {pitching_path}")
            
            self._loaded = self.batting_df is not None or self.pitching_df is not None
            return self._loaded
        except Exception as e:
            print(f"Error loading stats data: {e}")
            return False
    
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
        Get year-by-year stats for a player.
        
        Args:
            player_name: Name of the player to look up
            is_pitcher: True for pitcher stats, False for batter stats
            num_years: Number of recent seasons to return (default 3)
            
        Returns:
            List of dicts containing stats for each season found
        """
        if not self._loaded:
            return []
        
        df = self.pitching_df if is_pitcher else self.batting_df
        if df is None:
            return []
        
        # Get the years to query
        years = self.get_recent_completed_seasons(num_years)
        
        # Normalize search name
        search_name = self.normalize_name(player_name)
        
        # Create normalized name column for matching if not exists
        if 'name_normalized' not in df.columns:
            df['name_normalized'] = df['Name'].apply(self.normalize_name)
        
        # Filter by name and years
        matches = df[
            (df['name_normalized'] == search_name) & 
            (df['Season'].isin(years))
        ].sort_values('Season')
        
        results = []
        for _, row in matches.iterrows():
            if is_pitcher:
                results.append({
                    'season': int(row['Season']),
                    'team': str(row.get('Team', '')),
                    'war': float(row['WAR']) if pd.notna(row.get('WAR')) else None,
                    'era': float(row['ERA']) if pd.notna(row.get('ERA')) else None,
                    'fip': float(row['FIP']) if pd.notna(row.get('FIP')) else None,
                    'k_9': float(row['K/9']) if pd.notna(row.get('K/9')) else None,
                    'bb_9': float(row['BB/9']) if pd.notna(row.get('BB/9')) else None,
                    'ip': float(row['IP']) if pd.notna(row.get('IP')) else None,
                    'games': int(row['G']) if pd.notna(row.get('G')) else None,
                    'wins': int(row['W']) if pd.notna(row.get('W')) else None,
                    'losses': int(row['L']) if pd.notna(row.get('L')) else None,
                })
            else:
                results.append({
                    'season': int(row['Season']),
                    'team': str(row.get('Team', '')),
                    'war': float(row['WAR']) if pd.notna(row.get('WAR')) else None,
                    'wrc_plus': float(row['wRC+']) if pd.notna(row.get('wRC+')) else None,
                    'avg': float(row['AVG']) if pd.notna(row.get('AVG')) else None,
                    'obp': float(row['OBP']) if pd.notna(row.get('OBP')) else None,
                    'slg': float(row['SLG']) if pd.notna(row.get('SLG')) else None,
                    'hr': int(row['HR']) if pd.notna(row.get('HR')) else None,
                    'rbi': int(row['RBI']) if pd.notna(row.get('RBI')) else None,
                    'sb': int(row['SB']) if pd.notna(row.get('SB')) else None,
                    'runs': int(row['R']) if pd.notna(row.get('R')) else None,
                    'hits': int(row['H']) if pd.notna(row.get('H')) else None,
                    'games': int(row['G']) if pd.notna(row.get('G')) else None,
                    'pa': int(row['PA']) if pd.notna(row.get('PA')) else None,
                })
        
        return results
    
    @property
    def is_loaded(self) -> bool:
        """Check if data has been loaded."""
        return self._loaded


# Singleton instance for use across the application
stats_service = StatsService()

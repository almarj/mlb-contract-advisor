"""
MLB Contract Advisor - Statcast Data Collection Script
Starter script for collecting player performance metrics for contract predictions

Author: MLB Contract Advisor Team
Date: January 2026
"""

import pandas as pd
from pybaseball import cache
from pybaseball import (
    playerid_lookup,
    statcast_batter_exitvelo_barrels,
    statcast_batter_percentile_ranks,
    statcast_pitcher_exitvelo_barrels,
    statcast_pitcher_percentile_ranks,
    batting_stats,
    pitching_stats
)
import time

# CRITICAL: Enable caching to avoid re-downloading data
cache.enable()

print("=" * 60)
print("MLB CONTRACT ADVISOR - STATCAST DATA COLLECTION")
print("=" * 60)

# ============================================================================
# CONFIGURATION
# ============================================================================

# Years to collect data for (2015-2024)
# Note: Statcast batting metrics (exit velo, barrels) only available from 2015+
START_YEAR = 2015
END_YEAR = 2024

# Sample player list (you'll replace this with your Spotrac contract data)
# Format: (last_name, first_name, position, year_signed)
SAMPLE_PLAYERS = [
    ('Judge', 'Aaron', 'OF', 2023),
    ('Betts', 'Mookie', 'OF', 2020),
    ('deGrom', 'Jacob', 'P', 2023),
    ('Ohtani', 'Shohei', 'DH', 2024),
]

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_mlbam_player_id(last_name, first_name):
    """
    Get MLB Advanced Media player ID for use with Statcast functions
    
    Args:
        last_name (str): Player's last name
        first_name (str): Player's first name
        
    Returns:
        int or None: MLBAM player ID or None if not found
    """
    try:
        result = playerid_lookup(last_name, first_name)
        if len(result) > 0:
            # Return the most recent player (last row)
            player_id = result.iloc[-1]['key_mlbam']
            print(f"  ✓ Found {first_name} {last_name} (ID: {player_id})")
            return player_id
        else:
            print(f"  ✗ No match found for {first_name} {last_name}")
            return None
    except Exception as e:
        print(f"  ✗ Error looking up {first_name} {last_name}: {str(e)}")
        return None


def collect_batter_statcast_season(year, min_bbe=25):
    """
    Collect Statcast batting metrics for a single season
    
    Args:
        year (int): Season year
        min_bbe (int): Minimum batted ball events (default: 25)
        
    Returns:
        pandas.DataFrame: Statcast batting data
    """
    print(f"\nCollecting batter Statcast data for {year}...")
    
    try:
        # Get exit velocity and barrel data
        exitvelo_data = statcast_batter_exitvelo_barrels(year, min_bbe)
        print(f"  ✓ Exit velocity/barrels: {len(exitvelo_data)} players")
        
        # Get percentile ranks (includes sprint speed)
        percentile_data = statcast_batter_percentile_ranks(year)
        print(f"  ✓ Percentile ranks: {len(percentile_data)} players")
        
        # Merge the datasets on player_id
        merged = pd.merge(
            exitvelo_data,
            percentile_data[['player_id', 'sprint_speed']],
            on='player_id',
            how='left'
        )
        
        return merged
        
    except Exception as e:
        print(f"  ✗ Error collecting {year} batter data: {str(e)}")
        return pd.DataFrame()


def collect_pitcher_statcast_season(year, min_bbe=25):
    """
    Collect Statcast pitching metrics for a single season
    
    Args:
        year (int): Season year
        min_bbe (int): Minimum batted ball events against (default: 25)
        
    Returns:
        pandas.DataFrame: Statcast pitching data
    """
    print(f"\nCollecting pitcher Statcast data for {year}...")
    
    try:
        # Get batted ball data against
        pitcher_data = statcast_pitcher_exitvelo_barrels(year, min_bbe)
        print(f"  ✓ Exit velocity/barrels allowed: {len(pitcher_data)} players")
        
        return pitcher_data
        
    except Exception as e:
        print(f"  ✗ Error collecting {year} pitcher data: {str(e)}")
        return pd.DataFrame()


def collect_fangraphs_batting_stats(start_year, end_year):
    """
    Collect comprehensive batting stats from FanGraphs (includes WAR, wRC+)
    
    Args:
        start_year (int): First season
        end_year (int): Last season
        
    Returns:
        pandas.DataFrame: FanGraphs batting data
    """
    print(f"\nCollecting FanGraphs batting stats ({start_year}-{end_year})...")
    
    try:
        stats = batting_stats(start_year, end_year)
        print(f"  ✓ Collected {len(stats)} player-seasons")
        return stats
    except Exception as e:
        print(f"  ✗ Error collecting FanGraphs data: {str(e)}")
        return pd.DataFrame()


def collect_fangraphs_pitching_stats(start_year, end_year):
    """
    Collect comprehensive pitching stats from FanGraphs (includes WAR, ERA+)
    
    Args:
        start_year (int): First season
        end_year (int): Last season
        
    Returns:
        pandas.DataFrame: FanGraphs pitching data
    """
    print(f"\nCollecting FanGraphs pitching stats ({start_year}-{end_year})...")
    
    try:
        stats = pitching_stats(start_year, end_year)
        print(f"  ✓ Collected {len(stats)} player-seasons")
        return stats
    except Exception as e:
        print(f"  ✗ Error collecting FanGraphs data: {str(e)}")
        return pd.DataFrame()


def calculate_3year_averages(player_id, stat_df, year_signed, metrics):
    """
    Calculate 3-year average of specified metrics for a player
    
    Args:
        player_id (int): MLBAM player ID
        stat_df (DataFrame): Stats dataframe with 'player_id', 'year_season' columns
        year_signed (int): Year the contract was signed
        metrics (list): List of column names to average
        
    Returns:
        dict: Dictionary of 3-year averages
    """
    # Get stats from 3 years prior to signing (year-3, year-2, year-1)
    years = [year_signed - 3, year_signed - 2, year_signed - 1]
    
    # Filter for this player and these years
    player_stats = stat_df[
        (stat_df['player_id'] == player_id) & 
        (stat_df['year_season'].isin(years))
    ]
    
    if len(player_stats) == 0:
        return {f'{metric}_3yr_avg': None for metric in metrics}
    
    # Calculate averages
    averages = {}
    for metric in metrics:
        if metric in player_stats.columns:
            averages[f'{metric}_3yr_avg'] = player_stats[metric].mean()
        else:
            averages[f'{metric}_3yr_avg'] = None
    
    return averages


# ============================================================================
# MAIN EXECUTION
# ============================================================================

def main():
    """
    Main execution function - demonstrates data collection workflow
    """
    
    print("\n" + "=" * 60)
    print("STEP 1: PLAYER ID LOOKUP")
    print("=" * 60)
    
    # Example: Get player IDs for sample players
    player_ids = []
    for last, first, pos, year in SAMPLE_PLAYERS:
        player_id = get_mlbam_player_id(last, first)
        if player_id:
            player_ids.append({
                'name': f'{first} {last}',
                'player_id': player_id,
                'position': pos,
                'year_signed': year
            })
        time.sleep(1)  # Be nice to the API
    
    print(f"\n✓ Successfully found {len(player_ids)} / {len(SAMPLE_PLAYERS)} players")
    
    
    print("\n" + "=" * 60)
    print("STEP 2: COLLECT SEASON-LEVEL STATCAST DATA")
    print("=" * 60)
    
    # Collect one year of batter data as example
    batter_statcast_2024 = collect_batter_statcast_season(2024)
    print(f"\nBatter Statcast 2024 columns:")
    print(batter_statcast_2024.columns.tolist()[:20], "...")  # Show first 20 columns
    
    # Collect one year of pitcher data as example
    pitcher_statcast_2024 = collect_pitcher_statcast_season(2024)
    print(f"\nPitcher Statcast 2024 columns:")
    print(pitcher_statcast_2024.columns.tolist()[:20], "...")
    
    
    print("\n" + "=" * 60)
    print("STEP 3: COLLECT FANGRAPHS DATA (WAR, wRC+, ERA+)")
    print("=" * 60)
    
    # Collect FanGraphs data for recent years (example: 2022-2024)
    fg_batting = collect_fangraphs_batting_stats(2022, 2024)
    fg_pitching = collect_fangraphs_pitching_stats(2022, 2024)
    
    print(f"\nFanGraphs batting important columns:")
    important_batting_cols = ['Name', 'Season', 'WAR', 'wRC+', 'AVG', 'OBP', 'SLG', 'HR', 'RBI', 'SB']
    available_cols = [col for col in important_batting_cols if col in fg_batting.columns]
    print(available_cols)
    
    print(f"\nFanGraphs pitching important columns:")
    important_pitching_cols = ['Name', 'Season', 'WAR', 'ERA', 'FIP', 'K/9', 'BB/9', 'IP', 'W', 'L']
    available_cols = [col for col in important_pitching_cols if col in fg_pitching.columns]
    print(available_cols)
    
    
    print("\n" + "=" * 60)
    print("STEP 4: EXAMPLE - GET DATA FOR AARON JUDGE")
    print("=" * 60)
    
    # Find Aaron Judge in our sample
    judge = next((p for p in player_ids if 'Judge' in p['name']), None)
    
    if judge:
        judge_id = judge['player_id']
        print(f"\nAaron Judge (ID: {judge_id}) signed in {judge['year_signed']}")
        print("Looking for his stats from the year before signing...")
        
        # Get his 2022 stats (year before 2023 signing)
        judge_2022_statcast = batter_statcast_2024[
            batter_statcast_2024['player_id'] == judge_id
        ]
        
        if not judge_2022_statcast.empty:
            print("\nAaron Judge 2024 Statcast metrics:")
            print(f"  Exit Velocity: {judge_2022_statcast['avg_hit_speed'].values[0]:.1f} mph")
            print(f"  Barrel %: {judge_2022_statcast['barrel_batted_rate'].values[0]:.1f}%")
            print(f"  Max Exit Velo: {judge_2022_statcast['max_hit_speed'].values[0]:.1f} mph")
    
    
    print("\n" + "=" * 60)
    print("DATA COLLECTION COMPLETE")
    print("=" * 60)
    print("\nNext Steps:")
    print("1. Export this data to CSV files")
    print("2. Load your Spotrac contract data")
    print("3. Match contracts to player stats using player_id")
    print("4. Calculate 3-year averages for model training")
    print("5. Store in PostgreSQL database")
    
    # Optional: Save sample data
    print("\n" + "=" * 60)
    print("SAVING SAMPLE DATA")
    print("=" * 60)
    
    if not batter_statcast_2024.empty:
        batter_statcast_2024.to_csv('batter_statcast_2024_sample.csv', index=False)
        print("✓ Saved: batter_statcast_2024_sample.csv")
    
    if not pitcher_statcast_2024.empty:
        pitcher_statcast_2024.to_csv('pitcher_statcast_2024_sample.csv', index=False)
        print("✓ Saved: pitcher_statcast_2024_sample.csv")
    
    if not fg_batting.empty:
        fg_batting.to_csv('fangraphs_batting_2022-2024.csv', index=False)
        print("✓ Saved: fangraphs_batting_2022-2024.csv")
    
    if not fg_pitching.empty:
        fg_pitching.to_csv('fangraphs_pitching_2022-2024.csv', index=False)
        print("✓ Saved: fangraphs_pitching_2022-2024.csv")
    
    print("\n✓ All done! Check the CSV files to see the data structure.")


if __name__ == "__main__":
    main()

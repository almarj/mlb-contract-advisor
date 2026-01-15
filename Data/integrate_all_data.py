"""
MLB Contract Advisor - Data Integration Script
Merge Spotrac contracts + FanGraphs stats + Statcast metrics

This script shows you how to combine all three data sources into one dataset
for your ML model training.
"""

import pandas as pd
import numpy as np
from pybaseball import cache, statcast_batter_exitvelo_barrels, statcast_pitcher_exitvelo_barrels

cache.enable()

print("=" * 80)
print("MLB CONTRACT ADVISOR - DATA INTEGRATION")
print("=" * 80)

# ============================================================================
# STEP 1: Load Your Existing Data
# ============================================================================
print("\n[STEP 1] Loading existing data...")

# Load FanGraphs data (you already have this)
try:
    fg_batting = pd.read_csv('fangraphs_batting_2015-2025.csv')
    print(f"✓ Loaded FanGraphs batting: {len(fg_batting)} player-seasons")
except FileNotFoundError:
    print("✗ Error: fangraphs_batting_2015-2025.csv not found")
    print("  Run collect_all_data.py first!")
    exit()

try:
    fg_pitching = pd.read_csv('fangraphs_pitching_2015-2025.csv')
    print(f"✓ Loaded FanGraphs pitching: {len(fg_pitching)} player-seasons")
except FileNotFoundError:
    print("✗ Error: fangraphs_pitching_2015-2025.csv not found")
    exit()

# ============================================================================
# STEP 2: Load Contract Data (YOU NEED TO CREATE THIS)
# ============================================================================
print("\n[STEP 2] Loading contract data...")

# IMPORTANT: You need to create this CSV from Spotrac data
# For now, we'll create a SAMPLE to show you the structure

print("\n⚠️  WARNING: Using SAMPLE contract data for demonstration")
print("    You need to replace this with actual Spotrac data!")

# Load actual Spotrac contract data
contracts = pd.read_csv('spotrac_contracts_2015-2025.csv')

print(f"✓ Loaded contract data: {len(sample_contracts)} contracts")
print("\nSample contracts:")
print(sample_contracts[['player_name', 'position', 'year_signed', 'AAV']].to_string(index=False))

# ============================================================================
# STEP 3: Function to Calculate 3-Year Averages
# ============================================================================
print("\n[STEP 3] Creating function to calculate 3-year averages...")

def get_3year_avg_stats(player_name, year_signed, stats_df, is_pitcher=False):
    """
    Get 3-year average stats for a player before they signed their contract.
    
    Args:
        player_name: Player's name
        year_signed: Year the contract was signed
        stats_df: DataFrame with FanGraphs stats
        is_pitcher: True for pitchers, False for batters
    
    Returns:
        Dictionary with 3-year averages
    """
    # Get stats from 3 years prior to signing (year-3, year-2, year-1)
    stats_year = year_signed - 1  # Use year before signing
    years_to_avg = [stats_year - 2, stats_year - 1, stats_year]
    
    # Filter for this player and these years
    player_stats = stats_df[
        (stats_df['Name'] == player_name) & 
        (stats_df['Season'].isin(years_to_avg))
    ]
    
    if len(player_stats) == 0:
        print(f"  ⚠️  No stats found for {player_name} in years {years_to_avg}")
        return None
    
    # Calculate averages for key metrics
    if is_pitcher:
        avg_stats = {
            'WAR_3yr': player_stats['WAR'].mean(),
            'ERA_3yr': player_stats['ERA'].mean(),
            'FIP_3yr': player_stats['FIP'].mean(),
            'K/9_3yr': player_stats['K/9'].mean(),
            'BB/9_3yr': player_stats['BB/9'].mean(),
            'IP_3yr': player_stats['IP'].mean(),
            'seasons_with_data': len(player_stats)
        }
    else:
        avg_stats = {
            'WAR_3yr': player_stats['WAR'].mean(),
            'wRC+_3yr': player_stats['wRC+'].mean(),
            'AVG_3yr': player_stats['AVG'].mean(),
            'OBP_3yr': player_stats['OBP'].mean(),
            'SLG_3yr': player_stats['SLG'].mean(),
            'HR_3yr': player_stats['HR'].mean(),
            'seasons_with_data': len(player_stats)
        }
    
    return avg_stats

print("✓ Function created")

# ============================================================================
# STEP 4: Get Statcast Data for Relevant Years
# ============================================================================
print("\n[STEP 4] Collecting Statcast data for contract years...")

# Get unique years from contracts
contract_years = sample_contracts['year_signed'].unique()
print(f"Contract years: {sorted(contract_years)}")

# Collect Statcast data for year before each contract signing
statcast_batting_data = {}
statcast_pitching_data = {}

for year in contract_years:
    stats_year = year - 1  # Get stats from year before signing
    
    if stats_year >= 2015:  # Statcast only available from 2015+
        try:
            print(f"\n  Collecting Statcast data for {stats_year}...")
            statcast_batting_data[stats_year] = statcast_batter_exitvelo_barrels(stats_year, minBBE=25)
            print(f"    ✓ Batting: {len(statcast_batting_data[stats_year])} players")
            
            statcast_pitching_data[stats_year] = statcast_pitcher_exitvelo_barrels(stats_year, minBBE=25)
            print(f"    ✓ Pitching: {len(statcast_pitching_data[stats_year])} pitchers")
        except Exception as e:
            print(f"    ✗ Error collecting {stats_year}: {e}")

# ============================================================================
# STEP 5: Merge Everything Together
# ============================================================================
print("\n[STEP 5] Merging all data sources...")

# Create master dataset
master_data = []

for idx, contract in sample_contracts.iterrows():
    player_name = contract['player_name']
    year_signed = contract['year_signed']
    position = contract['position']
    is_pitcher = position in ['SP', 'RP', 'P']
    
    print(f"\nProcessing: {player_name} ({position}, signed {year_signed})")
    
    # Get 3-year averages from FanGraphs
    stats_df = fg_pitching if is_pitcher else fg_batting
    avg_stats = get_3year_avg_stats(player_name, year_signed, stats_df, is_pitcher)
    
    if avg_stats is None:
        print(f"  ⚠️  Skipping {player_name} - no FanGraphs data")
        continue
    
    print(f"  ✓ FanGraphs 3yr avg: WAR={avg_stats['WAR_3yr']:.2f}")
    
    # Get Statcast metrics (if available)
    stats_year = year_signed - 1
    statcast_metrics = {}
    
    if stats_year >= 2015 and stats_year in statcast_batting_data:
        if is_pitcher:
            # Find pitcher in Statcast data
            pitcher_statcast = statcast_pitching_data[stats_year]
            # Match by name (you might need better matching logic)
            player_match = pitcher_statcast[
                pitcher_statcast['last_name, first_name'].str.contains(player_name.split()[-1], case=False, na=False)
            ]
            if len(player_match) > 0:
                statcast_metrics = {
                    'avg_hit_speed_against': player_match.iloc[0]['avg_hit_speed'],
                    'barrel_rate_against': player_match.iloc[0]['brl_percent']
                }
                print(f"  ✓ Statcast: Exit velo against={statcast_metrics['avg_hit_speed_against']:.1f} mph")
        else:
            # Find batter in Statcast data
            batter_statcast = statcast_batting_data[stats_year]
            player_match = batter_statcast[
                batter_statcast['last_name, first_name'].str.contains(player_name.split()[-1], case=False, na=False)
            ]
            if len(player_match) > 0:
                statcast_metrics = {
                    'avg_exit_velo': player_match.iloc[0]['avg_hit_speed'],
                    'barrel_rate': player_match.iloc[0]['brl_percent'],
                    'max_exit_velo': player_match.iloc[0]['max_hit_speed'],
                    'hard_hit_pct': player_match.iloc[0]['ev95percent']
                }
                print(f"  ✓ Statcast: Exit velo={statcast_metrics['avg_exit_velo']:.1f} mph, Barrels={statcast_metrics['barrel_rate']:.1f}%")
    
    # Combine everything
    master_row = {
        # Contract info
        'player_name': player_name,
        'position': position,
        'year_signed': year_signed,
        'age_at_signing': contract['age_at_signing'],
        'AAV': contract['AAV'],
        'total_value': contract['total_value'],
        'length': contract['length'],
        'team': contract['team'],
        
        # FanGraphs 3-year averages
        **avg_stats,
        
        # Statcast metrics
        **statcast_metrics
    }
    
    master_data.append(master_row)

# Convert to DataFrame
master_df = pd.DataFrame(master_data)

# ============================================================================
# STEP 6: Save Master Dataset
# ============================================================================
print("\n[STEP 6] Saving integrated dataset...")

master_df.to_csv('master_contract_dataset.csv', index=False)
print(f"✓ Saved to: master_contract_dataset.csv")
print(f"  Total contracts: {len(master_df)}")
print(f"  Total features: {len(master_df.columns)}")

# Show preview
print("\nPreview of master dataset:")
display_cols = ['player_name', 'age_at_signing', 'WAR_3yr', 'AAV', 'length']
if 'wRC+_3yr' in master_df.columns:
    display_cols.append('wRC+_3yr')
if 'avg_exit_velo' in master_df.columns:
    display_cols.append('avg_exit_velo')

print(master_df[display_cols].to_string(index=False))

# ============================================================================
# SUMMARY & NEXT STEPS
# ============================================================================
print("\n" + "=" * 80)
print("INTEGRATION COMPLETE!")
print("=" * 80)

print("\nWhat you have now:")
print("  ✓ Master dataset combining contracts + FanGraphs + Statcast")
print("  ✓ 3-year averages for each player")
print("  ✓ Ready for ML model training")

print("\nDataset columns:")
for i, col in enumerate(master_df.columns, 1):
    print(f"  {i:2d}. {col}")

print("\nNext steps:")
print("  1. Replace sample_contracts with your actual Spotrac data")
print("  2. Review and clean the master dataset")
print("  3. Handle missing Statcast data (pre-2015 or non-qualified players)")
print("  4. Set up PostgreSQL database")
print("  5. Begin ML model training (Phase 1 of your timeline)")

print("\nData quality checks needed:")
print("  • Verify player name matching (FanGraphs vs Statcast)")
print("  • Check for missing values")
print("  • Validate 3-year averages make sense")
print("  • Ensure AAV and contract values are correct")

print("\n" + "=" * 80)

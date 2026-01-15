"""
MLB Contract Advisor - Data Integration Script (CUSTOM FOR YOUR SPOTRAC DATA)
Merge Spotrac contracts + FanGraphs stats + Statcast metrics

This version is customized to work with your exact Spotrac CSV format.
"""

import pandas as pd
import numpy as np
from pybaseball import cache, statcast_batter_exitvelo_barrels, statcast_pitcher_percentile_ranks

cache.enable()

print("=" * 80)
print("MLB CONTRACT ADVISOR - DATA INTEGRATION")
print("=" * 80)

# ============================================================================
# STEP 1: Load Spotrac Contract Data
# ============================================================================
print("\n[STEP 1] Loading Spotrac contract data...")

try:
    contracts = pd.read_csv('spotract_contracts_2015-2025.csv')
    print(f"✓ Loaded {len(contracts)} contracts from Spotrac")
    
    # Clean up the data
    # Remove extra spaces from column names
    contracts.columns = contracts.columns.str.strip()
    
    # Rename columns to match our expected format
    contracts = contracts.rename(columns={
        'Player': 'player_name',
        'Pos': 'position',
        'Age                     At Signing': 'age_at_signing',
        'Start': 'year_signed',
        'Yrs': 'length',
        'Value': 'total_value',
        'AAV': 'AAV'
    })
    
    # Clean currency values (remove $ and commas)
    contracts['AAV'] = contracts['AAV'].str.replace('$', '').str.replace(',', '').astype(float)
    contracts['total_value'] = contracts['total_value'].str.replace('$', '').str.replace(',', '').astype(float)
    
    # Convert year to int
    contracts['year_signed'] = contracts['year_signed'].astype(int)
    contracts['length'] = contracts['length'].astype(int)
    contracts['age_at_signing'] = contracts['age_at_signing'].astype(int)
    
    print(f"\n✓ Cleaned contract data")
    print(f"  Date range: {contracts['year_signed'].min()}-{contracts['year_signed'].max()}")
    print(f"  Positions: {contracts['position'].unique()}")
    
except FileNotFoundError:
    print("✗ Error: spotract_contracts_2015-2025.csv not found")
    print("  Make sure the file is in your current directory!")
    exit()

# Show sample
print("\nSample contracts:")
print(contracts[['player_name', 'position', 'year_signed', 'age_at_signing', 'AAV']].head(10).to_string(index=False))

# ============================================================================
# STEP 2: Load FanGraphs Data
# ============================================================================
print("\n[STEP 2] Loading FanGraphs data...")

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
# STEP 3: Function to Calculate 3-Year Averages
# ============================================================================
print("\n[STEP 3] Creating function to calculate 3-year averages...")

def get_3year_avg_stats(player_name, year_signed, stats_df, is_pitcher=False):
    """
    Get 3-year average stats for a player before they signed their contract.
    """
    # Get stats from 3 years prior to signing (year-3, year-2, year-1)
    stats_year = year_signed - 1  # Use year before signing
    years_to_avg = [stats_year - 2, stats_year - 1, stats_year]
    
    # Filter for this player and these years
    player_stats = stats_df[
        (stats_df['Name'].str.strip() == player_name.strip()) & 
        (stats_df['Season'].isin(years_to_avg))
    ]
    
    if len(player_stats) == 0:
        # Try partial name match
        player_stats = stats_df[
            (stats_df['Name'].str.contains(player_name.split()[-1], case=False, na=False)) & 
            (stats_df['Season'].isin(years_to_avg))
        ]
        
        if len(player_stats) > 1:
            # Multiple matches, try to narrow down
            player_stats = player_stats[
                player_stats['Name'].str.contains(player_name.split()[0], case=False, na=False)
            ]
    
    if len(player_stats) == 0:
        return None, None
    
    # If multiple matches still exist, take the first one
    if len(player_stats) > 3:
        player_stats = player_stats.head(3)
    
    # Calculate averages for key metrics
    if is_pitcher:
        avg_stats = {
            'WAR_3yr': player_stats['WAR'].mean(),
            'ERA_3yr': player_stats['ERA'].mean(),
            'FIP_3yr': player_stats['FIP'].mean(),
            'K_9_3yr': player_stats['K/9'].mean() if 'K/9' in player_stats.columns else None,
            'BB_9_3yr': player_stats['BB/9'].mean() if 'BB/9' in player_stats.columns else None,
            'IP_3yr': player_stats['IP'].mean(),
            'seasons_with_data': len(player_stats)
        }
    else:
        avg_stats = {
            'WAR_3yr': player_stats['WAR'].mean(),
            'wRC_plus_3yr': player_stats['wRC+'].mean() if 'wRC+' in player_stats.columns else None,
            'AVG_3yr': player_stats['AVG'].mean() if 'AVG' in player_stats.columns else None,
            'OBP_3yr': player_stats['OBP'].mean() if 'OBP' in player_stats.columns else None,
            'SLG_3yr': player_stats['SLG'].mean() if 'SLG' in player_stats.columns else None,
            'HR_3yr': player_stats['HR'].mean() if 'HR' in player_stats.columns else None,
            'seasons_with_data': len(player_stats)
        }
    
    matched_name = player_stats.iloc[0]['Name'] if len(player_stats) > 0 else None
    return avg_stats, matched_name

print("✓ Function created")

# ============================================================================
# STEP 4: Get Statcast Data for Relevant Years
# ============================================================================
print("\n[STEP 4] Collecting Statcast data...")
print("This may take a few minutes on first run...")

# Get unique years from contracts (only years 2015+)
contract_years = contracts[contracts['year_signed'] >= 2015]['year_signed'].unique()
print(f"Contract years needing Statcast: {sorted(contract_years)}")

# Collect Statcast data for year before each contract signing
statcast_batting_data = {}

for year in sorted(contract_years):
    stats_year = year - 1  # Get stats from year before signing
    
    if stats_year >= 2015:  # Statcast only available from 2015+
        if stats_year not in statcast_batting_data:
            try:
                print(f"  Collecting Statcast batting for {stats_year}...", end='')
                statcast_batting_data[stats_year] = statcast_batter_exitvelo_barrels(stats_year, minBBE=25)
                print(f" ✓ {len(statcast_batting_data[stats_year])} players")
            except Exception as e:
                print(f" ✗ Error: {e}")

# ============================================================================
# STEP 5: Merge Everything Together
# ============================================================================
print("\n[STEP 5] Merging all data sources...")

master_data = []
failed_matches = []

for idx, contract in contracts.iterrows():
    player_name = contract['player_name']
    year_signed = contract['year_signed']
    position = contract['position']
    
    # Determine if pitcher
    is_pitcher = position in ['SP', 'RP', 'P', 'CL']
    
    if (idx + 1) % 10 == 0:
        print(f"  Processed {idx + 1}/{len(contracts)} contracts...")
    
    # Get 3-year averages from FanGraphs
    stats_df = fg_pitching if is_pitcher else fg_batting
    avg_stats, matched_name = get_3year_avg_stats(player_name, year_signed, stats_df, is_pitcher)
    
    if avg_stats is None:
        failed_matches.append({
            'player': player_name,
            'year': year_signed,
            'reason': 'No FanGraphs data found'
        })
        continue
    
    # Get Statcast metrics (if available)
    stats_year = year_signed - 1
    statcast_metrics = {}
    
    if not is_pitcher and stats_year >= 2015 and stats_year in statcast_batting_data:
        batter_statcast = statcast_batting_data[stats_year]
        
        # Try to match by last name
        last_name = player_name.split()[-1]
        player_match = batter_statcast[
            batter_statcast['last_name, first_name'].str.contains(last_name, case=False, na=False)
        ]
        
        if len(player_match) > 0:
            # If multiple matches, try to narrow with first name
            if len(player_match) > 1 and len(player_name.split()) > 1:
                first_name = player_name.split()[0]
                refined_match = player_match[
                    player_match['last_name, first_name'].str.contains(first_name, case=False, na=False)
                ]
                if len(refined_match) > 0:
                    player_match = refined_match
            
            statcast_metrics = {
                'avg_exit_velo': player_match.iloc[0]['avg_hit_speed'],
                'barrel_rate': player_match.iloc[0]['brl_percent'],
                'max_exit_velo': player_match.iloc[0]['max_hit_speed'],
                'hard_hit_pct': player_match.iloc[0]['ev95percent']
            }
    
    # Combine everything
    master_row = {
        # Contract info
        'player_name': player_name,
        'matched_fangraphs_name': matched_name,
        'position': position,
        'year_signed': year_signed,
        'age_at_signing': contract['age_at_signing'],
        'AAV': contract['AAV'],
        'total_value': contract['total_value'],
        'length': contract['length'],
        
        # FanGraphs 3-year averages
        **avg_stats,
        
        # Statcast metrics
        **statcast_metrics
    }
    
    master_data.append(master_row)

# Convert to DataFrame
master_df = pd.DataFrame(master_data)

print(f"\n✓ Successfully merged {len(master_df)} contracts")
print(f"  Failed to match: {len(failed_matches)} contracts")

if len(failed_matches) > 0:
    print("\nFailed matches (first 10):")
    for fail in failed_matches[:10]:
        print(f"  - {fail['player']} ({fail['year']}): {fail['reason']}")

# ============================================================================
# STEP 6: Save Master Dataset
# ============================================================================
print("\n[STEP 6] Saving integrated dataset...")

master_df.to_csv('master_contract_dataset.csv', index=False)
print(f"✓ Saved to: master_contract_dataset.csv")
print(f"  Total contracts: {len(master_df)}")
print(f"  Total features: {len(master_df.columns)}")

# Also save failed matches for review
if len(failed_matches) > 0:
    pd.DataFrame(failed_matches).to_csv('failed_matches.csv', index=False)
    print(f"✓ Saved failed matches to: failed_matches.csv")

# ============================================================================
# STEP 7: Data Quality Summary
# ============================================================================
print("\n[STEP 7] Data Quality Summary")
print("=" * 80)

# Count missing values
print("\nMissing value counts:")
for col in master_df.columns:
    missing = master_df[col].isna().sum()
    if missing > 0:
        pct = (missing / len(master_df)) * 100
        print(f"  {col}: {missing} ({pct:.1f}%)")

# Statcast coverage
if 'avg_exit_velo' in master_df.columns:
    has_statcast = master_df['avg_exit_velo'].notna().sum()
    pct = (has_statcast / len(master_df)) * 100
    print(f"\nStatcast coverage: {has_statcast}/{len(master_df)} contracts ({pct:.1f}%)")

# Show preview
print("\n" + "=" * 80)
print("Preview of master dataset (first 5 rows):")
print("=" * 80)

display_cols = ['player_name', 'position', 'year_signed', 'age_at_signing', 'WAR_3yr', 'AAV', 'length']
if 'wRC_plus_3yr' in master_df.columns:
    display_cols.append('wRC_plus_3yr')
if 'avg_exit_velo' in master_df.columns:
    display_cols.append('avg_exit_velo')

print(master_df[display_cols].head().to_string(index=False))

# Summary statistics
print("\n" + "=" * 80)
print("Summary Statistics:")
print("=" * 80)

print(f"\nContract Values:")
print(f"  Average AAV: ${master_df['AAV'].mean():,.0f}")
print(f"  Median AAV: ${master_df['AAV'].median():,.0f}")
print(f"  Max AAV: ${master_df['AAV'].max():,.0f} ({master_df.loc[master_df['AAV'].idxmax(), 'player_name']})")
print(f"  Min AAV: ${master_df['AAV'].min():,.0f} ({master_df.loc[master_df['AAV'].idxmin(), 'player_name']})")

print(f"\nContract Lengths:")
print(f"  Average: {master_df['length'].mean():.1f} years")
print(f"  Median: {master_df['length'].median():.0f} years")
print(f"  Range: {master_df['length'].min()}-{master_df['length'].max()} years")

print(f"\nWAR (3-year average):")
print(f"  Average: {master_df['WAR_3yr'].mean():.2f}")
print(f"  Median: {master_df['WAR_3yr'].median():.2f}")

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

print("\nFiles created:")
print("  1. master_contract_dataset.csv - Your main training data")
if len(failed_matches) > 0:
    print("  2. failed_matches.csv - Contracts that couldn't be matched")

print("\nDataset columns:")
for i, col in enumerate(master_df.columns, 1):
    print(f"  {i:2d}. {col}")

print("\nNext steps:")
print("  1. Review master_contract_dataset.csv in Excel")
print("  2. Check failed_matches.csv and manually fix if needed")
print("  3. Handle missing Statcast data (decide imputation strategy)")
print("  4. Set up PostgreSQL database and load this data")
print("  5. Begin ML model development (Phase 1 of your timeline)")

print("\n" + "=" * 80)

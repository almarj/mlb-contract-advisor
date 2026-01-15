"""
MLB Contract Advisor - Data Integration Script (IMPROVED NAME MATCHING)
========================================================================
Merge Spotrac contracts + FanGraphs stats + Statcast metrics

Key improvements over previous version:
- Handles accented characters (José → Jose)
- Handles name suffixes (Jr., II, III)
- Uses fuzzy matching for edge cases
- Better logging of match reasons
"""

import pandas as pd
import numpy as np
import unicodedata
import re
from pybaseball import cache, statcast_batter_exitvelo_barrels
import os

cache.enable()

# Output directory
OUTPUT_DIR = 'Master Data'
os.makedirs(OUTPUT_DIR, exist_ok=True)

print("=" * 80)
print("MLB CONTRACT ADVISOR - IMPROVED DATA INTEGRATION")
print("=" * 80)


def normalize_name(name):
    """
    Normalize a player name for matching:
    - Remove accents (José → Jose)
    - Remove suffixes (Jr., II, III, Sr.)
    - Lowercase
    - Strip extra whitespace
    """
    if pd.isna(name):
        return ""

    # Convert to string
    name = str(name)

    # Remove accents using unicode normalization
    name = unicodedata.normalize('NFD', name)
    name = ''.join(c for c in name if unicodedata.category(c) != 'Mn')

    # Remove common suffixes
    suffixes = [' jr.', ' jr', ' sr.', ' sr', ' ii', ' iii', ' iv', ' v']
    name_lower = name.lower()
    for suffix in suffixes:
        if name_lower.endswith(suffix):
            name = name[:-len(suffix)]
            break

    # Remove punctuation except spaces and hyphens
    name = re.sub(r"[^\w\s\-]", "", name)

    # Normalize whitespace
    name = ' '.join(name.split())

    return name.lower().strip()


def get_name_parts(name):
    """Get first and last name components."""
    normalized = normalize_name(name)
    parts = normalized.split()
    if len(parts) >= 2:
        return parts[0], parts[-1]
    elif len(parts) == 1:
        return "", parts[0]
    return "", ""


def find_player_match(player_name, stats_df, years_to_avg):
    """
    Find a player in the stats DataFrame using multiple matching strategies.
    Returns (matched_stats_df, match_reason) or (None, reason).
    """
    normalized_target = normalize_name(player_name)
    first_name, last_name = get_name_parts(player_name)

    # Create normalized name column if not exists
    if '_normalized_name' not in stats_df.columns:
        stats_df['_normalized_name'] = stats_df['Name'].apply(normalize_name)

    # Filter to relevant years first
    year_filtered = stats_df[stats_df['Season'].isin(years_to_avg)].copy()

    if len(year_filtered) == 0:
        return None, "No data in year range"

    # Strategy 1: Exact normalized match
    exact_match = year_filtered[year_filtered['_normalized_name'] == normalized_target]
    if len(exact_match) > 0:
        return exact_match, "exact_normalized"

    # Strategy 2: Last name + first initial match
    if first_name and last_name:
        first_initial = first_name[0]
        partial_match = year_filtered[
            (year_filtered['_normalized_name'].str.contains(last_name, na=False)) &
            (year_filtered['_normalized_name'].str.startswith(first_initial))
        ]
        if len(partial_match) == 1 or (len(partial_match) > 0 and
            len(partial_match['_normalized_name'].unique()) == 1):
            return partial_match, "last_name_first_initial"

    # Strategy 3: Full last name match (for unique last names)
    if last_name:
        last_match = year_filtered[year_filtered['_normalized_name'].str.contains(f" {last_name}$|^{last_name} ", regex=True, na=False)]
        if len(last_match) > 0:
            unique_names = last_match['_normalized_name'].unique()
            if len(unique_names) == 1:
                return last_match, "unique_last_name"
            # Try adding first name filter
            if first_name:
                refined = last_match[last_match['_normalized_name'].str.contains(first_name, na=False)]
                if len(refined) > 0:
                    return refined, "last_name_partial_first"

    # Strategy 4: Contains both first and last name
    if first_name and last_name:
        contains_both = year_filtered[
            (year_filtered['_normalized_name'].str.contains(first_name, na=False)) &
            (year_filtered['_normalized_name'].str.contains(last_name, na=False))
        ]
        if len(contains_both) > 0:
            return contains_both, "contains_both_names"

    # Strategy 5: Partial last name (for hyphenated or compound names)
    if last_name and len(last_name) > 3:
        partial_last = year_filtered[year_filtered['_normalized_name'].str.contains(last_name[:4], na=False)]
        if len(partial_last) > 0 and len(partial_last['_normalized_name'].unique()) == 1:
            return partial_last, "partial_last_name"

    return None, "No match found"


def get_3year_avg_stats(player_name, year_signed, stats_df, is_pitcher=False):
    """
    Get 3-year average stats for a player before they signed their contract.
    """
    stats_year = year_signed - 1
    years_to_avg = [stats_year - 2, stats_year - 1, stats_year]

    # Find matching player data
    player_stats, match_reason = find_player_match(player_name, stats_df, years_to_avg)

    if player_stats is None or len(player_stats) == 0:
        return None, None, match_reason

    # Get unique player name from match
    matched_name = player_stats.iloc[0]['Name']

    # Calculate averages for key metrics
    if is_pitcher:
        avg_stats = {
            'WAR_3yr': player_stats['WAR'].mean(),
            'ERA_3yr': player_stats['ERA'].mean(),
            'FIP_3yr': player_stats['FIP'].mean(),
            'K_9_3yr': player_stats['K/9'].mean() if 'K/9' in player_stats.columns else None,
            'BB_9_3yr': player_stats['BB/9'].mean() if 'BB/9' in player_stats.columns else None,
            'IP_3yr': player_stats['IP'].mean() if 'IP' in player_stats.columns else None,
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

    return avg_stats, matched_name, match_reason


# ============================================================================
# STEP 1: Load Spotrac Contract Data
# ============================================================================
print("\n[STEP 1] Loading Spotrac contract data...")

try:
    contracts = pd.read_csv('spotract_contracts_2015-2025.csv')
    print(f"Loaded {len(contracts)} contracts from Spotrac")

    contracts.columns = contracts.columns.str.strip()

    contracts = contracts.rename(columns={
        'Player': 'player_name',
        'Pos': 'position',
        'Age                     At Signing': 'age_at_signing',
        'Start': 'year_signed',
        'Yrs': 'length',
        'Value': 'total_value',
        'AAV': 'AAV'
    })

    # Clean currency values
    contracts['AAV'] = contracts['AAV'].str.replace('$', '', regex=False).str.replace(',', '', regex=False)
    contracts['total_value'] = contracts['total_value'].str.replace('$', '', regex=False).str.replace(',', '', regex=False)

    contracts['AAV'] = pd.to_numeric(contracts['AAV'], errors='coerce')
    contracts['total_value'] = pd.to_numeric(contracts['total_value'], errors='coerce')
    contracts['year_signed'] = pd.to_numeric(contracts['year_signed'], errors='coerce')
    contracts['length'] = pd.to_numeric(contracts['length'], errors='coerce')
    contracts['age_at_signing'] = pd.to_numeric(contracts['age_at_signing'], errors='coerce')

    # Filter incomplete
    contracts = contracts[
        contracts['AAV'].notna() &
        contracts['year_signed'].notna() &
        contracts['age_at_signing'].notna() &
        contracts['length'].notna()
    ].copy()

    contracts['year_signed'] = contracts['year_signed'].astype(int)
    contracts['length'] = contracts['length'].astype(int)
    contracts['age_at_signing'] = contracts['age_at_signing'].astype(int)

    print(f"Valid contracts after cleaning: {len(contracts)}")
    print(f"Date range: {contracts['year_signed'].min()}-{contracts['year_signed'].max()}")

except FileNotFoundError:
    print("Error: spotract_contracts_2015-2025.csv not found")
    exit()

# ============================================================================
# STEP 2: Load FanGraphs Data
# ============================================================================
print("\n[STEP 2] Loading FanGraphs data...")

try:
    fg_batting = pd.read_csv('fangraphs_batting_2015-2025.csv')
    print(f"Loaded FanGraphs batting: {len(fg_batting)} player-seasons")
except FileNotFoundError:
    print("Error: fangraphs_batting_2015-2025.csv not found")
    exit()

try:
    fg_pitching = pd.read_csv('fangraphs_pitching_2015-2025.csv')
    print(f"Loaded FanGraphs pitching: {len(fg_pitching)} player-seasons")
except FileNotFoundError:
    print("Error: fangraphs_pitching_2015-2025.csv not found")
    exit()

# Pre-compute normalized names
print("\nNormalizing names for matching...")
fg_batting['_normalized_name'] = fg_batting['Name'].apply(normalize_name)
fg_pitching['_normalized_name'] = fg_pitching['Name'].apply(normalize_name)

print(f"  Unique batters: {fg_batting['_normalized_name'].nunique()}")
print(f"  Unique pitchers: {fg_pitching['_normalized_name'].nunique()}")

# ============================================================================
# STEP 3: Collect Statcast Data
# ============================================================================
print("\n[STEP 3] Collecting Statcast data...")

contract_years = contracts[contracts['year_signed'] >= 2016]['year_signed'].unique()
statcast_batting_data = {}

for year in sorted(contract_years):
    stats_year = year - 1
    if stats_year >= 2015 and stats_year not in statcast_batting_data:
        try:
            print(f"  Collecting Statcast for {stats_year}...", end='')
            statcast_batting_data[stats_year] = statcast_batter_exitvelo_barrels(stats_year, minBBE=25)
            print(f" ({len(statcast_batting_data[stats_year])} players)")
        except Exception as e:
            print(f" Error: {e}")

# ============================================================================
# STEP 4: Merge Everything Together
# ============================================================================
print("\n[STEP 4] Merging all data sources...")

master_data = []
failed_matches = []
match_reasons_count = {}

for idx, contract in contracts.iterrows():
    player_name = contract['player_name']
    year_signed = contract['year_signed']
    position = contract['position']

    is_pitcher = position in ['SP', 'RP', 'P', 'CL']

    if (idx + 1) % 100 == 0:
        print(f"  Processed {idx + 1}/{len(contracts)} contracts...")

    # Get 3-year averages from FanGraphs
    stats_df = fg_pitching if is_pitcher else fg_batting
    avg_stats, matched_name, match_reason = get_3year_avg_stats(player_name, year_signed, stats_df, is_pitcher)

    # Track match reasons
    match_reasons_count[match_reason] = match_reasons_count.get(match_reason, 0) + 1

    if avg_stats is None:
        failed_matches.append({
            'player': player_name,
            'year': year_signed,
            'position': position,
            'reason': match_reason
        })
        continue

    # Get Statcast metrics
    stats_year = year_signed - 1
    statcast_metrics = {}

    if not is_pitcher and stats_year >= 2015 and stats_year in statcast_batting_data:
        batter_statcast = statcast_batting_data[stats_year]

        # Normalize name for matching
        normalized_name = normalize_name(player_name)
        first_name, last_name = get_name_parts(player_name)

        player_match = batter_statcast[
            batter_statcast['last_name, first_name'].apply(
                lambda x: last_name in normalize_name(str(x)) if pd.notna(x) else False
            )
        ]

        if len(player_match) > 1 and first_name:
            player_match = player_match[
                player_match['last_name, first_name'].apply(
                    lambda x: first_name in normalize_name(str(x)) if pd.notna(x) else False
                )
            ]

        if len(player_match) > 0:
            statcast_metrics = {
                'avg_exit_velo': player_match.iloc[0]['avg_hit_speed'],
                'barrel_rate': player_match.iloc[0]['brl_percent'],
                'max_exit_velo': player_match.iloc[0]['max_hit_speed'],
                'hard_hit_pct': player_match.iloc[0]['ev95percent']
            }

    # Combine everything
    master_row = {
        'player_name': player_name,
        'matched_fangraphs_name': matched_name,
        'position': position,
        'year_signed': year_signed,
        'age_at_signing': contract['age_at_signing'],
        'AAV': contract['AAV'],
        'total_value': contract['total_value'],
        'length': contract['length'],
        **avg_stats,
        **statcast_metrics
    }

    master_data.append(master_row)

# Convert to DataFrame
master_df = pd.DataFrame(master_data)

# ============================================================================
# STEP 5: Report Results
# ============================================================================
print("\n" + "=" * 80)
print("INTEGRATION RESULTS")
print("=" * 80)

print(f"\nTotal contracts processed: {len(contracts)}")
print(f"Successfully matched: {len(master_df)} ({len(master_df)/len(contracts)*100:.1f}%)")
print(f"Failed to match: {len(failed_matches)} ({len(failed_matches)/len(contracts)*100:.1f}%)")

print("\nMatch reasons breakdown:")
for reason, count in sorted(match_reasons_count.items(), key=lambda x: -x[1]):
    print(f"  {reason}: {count}")

# ============================================================================
# STEP 6: Save Results
# ============================================================================
print("\n[STEP 5] Saving results...")

master_path = os.path.join(OUTPUT_DIR, 'master_contract_dataset.csv')
master_df.to_csv(master_path, index=False)
print(f"Saved: {master_path} ({len(master_df)} contracts)")

if len(failed_matches) > 0:
    failed_path = os.path.join(OUTPUT_DIR, 'failed_matches.csv')
    pd.DataFrame(failed_matches).to_csv(failed_path, index=False)
    print(f"Saved: {failed_path} ({len(failed_matches)} failures)")

# ============================================================================
# STEP 7: Summary Statistics
# ============================================================================
print("\n" + "=" * 80)
print("DATASET SUMMARY")
print("=" * 80)

# Position breakdown
print("\nPosition breakdown:")
for pos, count in master_df['position'].value_counts().items():
    print(f"  {pos}: {count}")

print(f"\nContract values:")
print(f"  Average AAV: ${master_df['AAV'].mean():,.0f}")
print(f"  Median AAV: ${master_df['AAV'].median():,.0f}")
print(f"  Max: ${master_df['AAV'].max():,.0f} ({master_df.loc[master_df['AAV'].idxmax(), 'player_name']})")

print(f"\nStatcast coverage:")
if 'avg_exit_velo' in master_df.columns:
    has_statcast = master_df['avg_exit_velo'].notna().sum()
    print(f"  {has_statcast}/{len(master_df)} contracts ({has_statcast/len(master_df)*100:.1f}%)")

print("\n" + "=" * 80)
print("INTEGRATION COMPLETE!")
print("=" * 80)
print(f"\nNext: Run train_contract_model.py to retrain with expanded dataset")

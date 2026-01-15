"""
MLB Contract Advisor - Expanded Data Collection
================================================
Collect FanGraphs data with LOWER qualification thresholds
to capture more players (especially younger/part-time players).

Default pybaseball thresholds: 502 PA (batters), 1 IP/team game (pitchers)
We use: 50 PA (batters), 10 IP (pitchers) to capture more players.
"""

from pybaseball import cache, batting_stats, pitching_stats
import pandas as pd

# Enable caching
cache.enable()

print("=" * 70)
print("MLB CONTRACT ADVISOR - EXPANDED DATA COLLECTION")
print("=" * 70)
print("\nUsing lower qualification thresholds to capture more players...")

# ============================================================================
# STEP 1: Get Batting Stats with LOW threshold
# ============================================================================
print("\n[1/2] Getting FanGraphs batting data (2015-2025)...")
print("      Using qual=50 (50 plate appearances minimum)")
print("      This may take a few minutes on first run...")

batting = batting_stats(2015, 2025, qual=50)

print(f"Downloaded {len(batting)} player-seasons")
print(f"Unique players: {batting['Name'].nunique()}")

# Save
batting.to_csv('fangraphs_batting_2015-2025.csv', index=False)
print(f"Saved to: fangraphs_batting_2015-2025.csv")

# ============================================================================
# STEP 2: Get Pitching Stats with LOW threshold
# ============================================================================
print("\n[2/2] Getting FanGraphs pitching data (2015-2025)...")
print("      Using qual=10 (10 innings pitched minimum)")

pitching = pitching_stats(2015, 2025, qual=10)

print(f"Downloaded {len(pitching)} player-seasons")
print(f"Unique players: {pitching['Name'].nunique()}")

# Save
pitching.to_csv('fangraphs_pitching_2015-2025.csv', index=False)
print(f"Saved to: fangraphs_pitching_2015-2025.csv")

# ============================================================================
# Summary
# ============================================================================
print("\n" + "=" * 70)
print("DATA COLLECTION COMPLETE!")
print("=" * 70)

print("\nFiles updated:")
print(f"  1. fangraphs_batting_2015-2025.csv ({len(batting)} player-seasons)")
print(f"  2. fangraphs_pitching_2015-2025.csv ({len(pitching)} player-seasons)")

print("\nYears breakdown (batting):")
for year in sorted(batting['Season'].unique()):
    count = len(batting[batting['Season'] == year])
    print(f"  {year}: {count} players")

print("\nNext: Run integrate_with_spotrac_improved.py to merge with contracts")

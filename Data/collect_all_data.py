from pybaseball import cache, batting_stats, pitching_stats, playerid_lookup
import pandas as pd

# CRITICAL: Enable caching
cache.enable()

print("=" * 70)
print("MLB CONTRACT ADVISOR - FULL DATA COLLECTION")
print("=" * 70)

# ============================================================================
# STEP 1: Get Batting Stats (2015-2025)
# ============================================================================
print("\n[1/3] Getting FanGraphs batting data (2015-2025)...")
print("This includes WAR, wRC+, and 299 other metrics")
print("First run takes 2-3 minutes, then cached instantly...")

batting = batting_stats(2015, 2025)

print(f"✓ Downloaded {len(batting)} player-seasons")
print(f"  Years covered: 2015-2025")
print(f"  Total columns: {len(batting.columns)}")

# Save it
batting.to_csv('fangraphs_batting_2015-2025.csv', index=False)
print(f"✓ Saved to: fangraphs_batting_2015-2025.csv")

# ============================================================================
# STEP 2: Get Pitching Stats (2015-2025)
# ============================================================================
print("\n[2/3] Getting FanGraphs pitching data (2015-2025)...")
print("This includes WAR, ERA, FIP, and 334 other metrics")

pitching = pitching_stats(2015, 2025)

print(f"✓ Downloaded {len(pitching)} player-seasons")
print(f"  Years covered: 2015-2025")
print(f"  Total columns: {len(pitching.columns)}")

# Save it
pitching.to_csv('fangraphs_pitching_2015-2025.csv', index=False)
print(f"✓ Saved to: fangraphs_pitching_2015-2025.csv")

# ============================================================================
# STEP 3: Show Example - Calculate 3-Year Average for a Player
# ============================================================================
print("\n[3/3] Example: Aaron Judge 3-year average before 2023 signing")

# Get Judge's stats from 2020-2022 (3 years before signing)
judge_stats = batting[
    (batting['Name'] == 'Aaron Judge') & 
    (batting['Season'].isin([2020, 2021, 2022]))
]

if not judge_stats.empty:
    print("\nAaron Judge individual seasons:")
    print(judge_stats[['Season', 'WAR', 'wRC+', 'HR', 'Age']].to_string(index=False))
    
    # Calculate 3-year averages (what goes in your model)
    war_3yr = judge_stats['WAR'].mean()
    wrc_3yr = judge_stats['wRC+'].mean()
    age_at_signing = 30  # He was 30 when he signed
    
    print(f"\n3-Year Averages (features for your model):")
    print(f"  Age: {age_at_signing}")
    print(f"  WAR (3yr avg): {war_3yr:.2f}")
    print(f"  wRC+ (3yr avg): {wrc_3yr:.0f}")
    
    print(f"\nActual Contract (Dec 2022):")
    print(f"  AAV: $40M")
    print(f"  Length: 9 years")
    print(f"  Total: $360M")

# ============================================================================
# SUMMARY
# ============================================================================
print("\n" + "=" * 70)
print("DATA COLLECTION COMPLETE!")
print("=" * 70)

print("\nFiles created:")
print("  1. fangraphs_batting_2015-2025.csv (batting stats)")
print("  2. fangraphs_pitching_2015-2025.csv (pitching stats)")

print("\nKey columns you'll use in your model:")
print("  Batters: Name, Season, Age, WAR, wRC+, AVG, OBP, SLG, HR, RBI, SB")
print("  Pitchers: Name, Season, Age, WAR, ERA, FIP, K/9, BB/9, IP, W, L")

print("\nNext steps:")
print("  1. Open the CSV files in Excel")
print("  2. Get your Spotrac contract data")
print("  3. Match player names and calculate 3-year averages")
print("  4. Optionally add Statcast metrics (exit velo, barrel rate)")
print("  5. Store everything in PostgreSQL")

print("\n" + "=" * 70)

"""
FanGraphs Data Collection - MLB Contract Advisor
Get WAR, wRC+, ERA+ and other metrics needed for contract predictions

This shows you how to get FanGraphs data using pybaseball (already installed!)
"""

from pybaseball import cache, batting_stats, pitching_stats
import pandas as pd

# Enable caching
cache.enable()

print("=" * 70)
print("FANGRAPHS DATA COLLECTION via pybaseball")
print("=" * 70)

# ============================================================================
# OPTION 1: Get Multi-Year Batting Stats (Recommended)
# ============================================================================
print("\nOPTION 1: Getting batting stats for 2022-2024...")
print("(Includes WAR, wRC+, and 299+ other metrics)")
print("First run takes 1-2 minutes, then cached...")

try:
    # Get 3 years of batting data
    batting = batting_stats(2022, 2024)
    
    print(f"\n✓ Success! Downloaded {len(batting)} player-seasons")
    print(f"  Total columns: {len(batting.columns)}")
    
    # Show the key columns you need for your model
    key_columns = ['Name', 'Season', 'Team', 'Age', 'WAR', 'wRC+', 
                   'AVG', 'OBP', 'SLG', 'HR', 'RBI', 'SB']
    
    print("\nKey columns for your model:")
    available_cols = [col for col in key_columns if col in batting.columns]
    print(f"  {available_cols}")
    
    # Show top 5 players by WAR in 2024
    batting_2024 = batting[batting['Season'] == 2024].nlargest(5, 'WAR')
    print("\nTop 5 Players by WAR in 2024:")
    print(batting_2024[['Name', 'Team', 'WAR', 'wRC+', 'HR', 'AVG']].to_string(index=False))
    
    # Save to CSV
    batting.to_csv('fangraphs_batting_2022-2024.csv', index=False)
    print(f"\n✓ Saved to: fangraphs_batting_2022-2024.csv")
    
except Exception as e:
    print(f"\n✗ Error: {e}")
    import traceback
    traceback.print_exc()

# ============================================================================
# OPTION 2: Get Multi-Year Pitching Stats
# ============================================================================
print("\n" + "=" * 70)
print("OPTION 2: Getting pitching stats for 2022-2024...")
print("(Includes WAR, ERA, FIP, K/9, BB/9, and 334+ other metrics)")

try:
    # Get 3 years of pitching data
    pitching = pitching_stats(2022, 2024)
    
    print(f"\n✓ Success! Downloaded {len(pitching)} player-seasons")
    print(f"  Total columns: {len(pitching.columns)}")
    
    # Show the key columns you need
    key_columns = ['Name', 'Season', 'Team', 'Age', 'WAR', 'ERA', 
                   'FIP', 'K/9', 'BB/9', 'IP', 'W', 'L', 'SV']
    
    print("\nKey columns for your model:")
    available_cols = [col for col in key_columns if col in pitching.columns]
    print(f"  {available_cols}")
    
    # Show top 5 pitchers by WAR in 2024
    pitching_2024 = pitching[pitching['Season'] == 2024].nlargest(5, 'WAR')
    print("\nTop 5 Pitchers by WAR in 2024:")
    print(pitching_2024[['Name', 'Team', 'WAR', 'ERA', 'FIP', 'IP']].to_string(index=False))
    
    # Save to CSV
    pitching.to_csv('fangraphs_pitching_2022-2024.csv', index=False)
    print(f"\n✓ Saved to: fangraphs_pitching_2022-2024.csv")
    
except Exception as e:
    print(f"\n✗ Error: {e}")
    import traceback
    traceback.print_exc()

# ============================================================================
# OPTION 3: Calculate 3-Year Averages (For Your Model)
# ============================================================================
print("\n" + "=" * 70)
print("OPTION 3: Calculate 3-year averages for a specific player")
print("=" * 70)

try:
    # Example: Get Aaron Judge's 3-year average WAR (2020-2022)
    # This would be used when he signed his contract in Dec 2022
    
    judge_stats = batting[
        (batting['Name'] == 'Aaron Judge') & 
        (batting['Season'].isin([2020, 2021, 2022]))
    ]
    
    if not judge_stats.empty:
        print("\nAaron Judge Stats (2020-2022):")
        print(judge_stats[['Season', 'WAR', 'wRC+', 'HR', 'AVG']].to_string(index=False))
        
        # Calculate 3-year averages
        war_3yr = judge_stats['WAR'].mean()
        wrc_3yr = judge_stats['wRC+'].mean()
        hr_3yr = judge_stats['HR'].mean()
        
        print(f"\n3-Year Averages (for contract prediction model):")
        print(f"  WAR: {war_3yr:.2f}")
        print(f"  wRC+: {wrc_3yr:.0f}")
        print(f"  HR: {hr_3yr:.1f}")
        
        print(f"\nActual contract signed (Dec 2022): 9 years, $40M AAV")
    else:
        print("Aaron Judge data not found in this dataset")
    
except Exception as e:
    print(f"\n✗ Error: {e}")

# ============================================================================
# ALL AVAILABLE COLUMNS
# ============================================================================
print("\n" + "=" * 70)
print("COMPLETE LIST OF AVAILABLE METRICS")
print("=" * 70)

print("\nBATTING STATS - All Available Columns:")
print("(Save these for reference - 299 total!)")
for i, col in enumerate(batting.columns, 1):
    print(f"  {i:3d}. {col}")

print("\n" + "-" * 70)
print("\nPITCHING STATS - All Available Columns:")
print("(334 total metrics!)")
for i, col in enumerate(pitching.columns, 1):
    print(f"  {i:3d}. {col}")

# ============================================================================
# SUMMARY
# ============================================================================
print("\n" + "=" * 70)
print("SUMMARY")
print("=" * 70)
print("\nWhat you now have:")
print("  ✓ FanGraphs batting data (2022-2024) with WAR, wRC+")
print("  ✓ FanGraphs pitching data (2022-2024) with WAR, ERA, FIP")
print("  ✓ CSV files you can open in Excel")
print("  ✓ Example of calculating 3-year averages")

print("\nKey metrics for your MLB Contract Advisor model:")
print("  Position Players: WAR, wRC+, Age")
print("  Pitchers: WAR, ERA+, FIP, Age")
print("  Both: Can be merged with Statcast metrics via player name/ID")

print("\nNext steps:")
print("  1. Open the CSV files in Excel to explore")
print("  2. Match these to your Spotrac contract data")
print("  3. Calculate 3-year averages for each contract signing")
print("  4. Merge with Statcast data (optional but improves accuracy)")
print("  5. Store in PostgreSQL for model training")

print("\n" + "=" * 70)

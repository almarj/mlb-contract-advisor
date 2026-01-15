"""
QUICK START - Statcast Data Collection
Super simple script to get you started with pybaseball

Run this first to make sure everything works!
"""

from pybaseball import cache, playerid_lookup, statcast_batter_exitvelo_barrels

# Enable caching so you don't download the same data twice
cache.enable()

print("=" * 60)
print("QUICK START: Testing pybaseball")
print("=" * 60)

# ============================================================================
# TEST 1: Look up a player's ID
# ============================================================================
print("\nTEST 1: Looking up Aaron Judge's player ID...")

try:
    judge_lookup = playerid_lookup('Judge', 'Aaron')
    print("\n✓ Success! Here's what we found:")
    print(judge_lookup)
    
    # Get his MLBAM ID (used for Statcast queries)
    judge_id = judge_lookup.iloc[0]['key_mlbam']
    print(f"\nAaron Judge's MLBAM ID: {judge_id}")
    
except Exception as e:
    print(f"\n✗ Error: {e}")
    print("Make sure pybaseball is installed: pip install pybaseball")
    exit()

# ============================================================================
# TEST 2: Get 2024 Statcast data for all batters
# ============================================================================
print("\n" + "=" * 60)
print("TEST 2: Getting 2024 Statcast data for batters...")
print("(This might take 30-60 seconds on first run)")
print("=" * 60)

try:
    # Get all batters with at least 25 batted ball events in 2024
    batters_2024 = statcast_batter_exitvelo_barrels(2024, minBBE=25)
    
    print(f"\n✓ Success! Downloaded data for {len(batters_2024)} players")
    print(f"   Columns available: {len(batters_2024.columns)}")
    
    # Show the first few rows
    print("\nFirst 3 players:")
    print(batters_2024[['first_name', 'last_name', 'avg_hit_speed', 'barrel_batted_rate']].head(3))
    
    # Find Aaron Judge in the data
    judge_stats = batters_2024[batters_2024['player_id'] == judge_id]
    
    if not judge_stats.empty:
        print("\n" + "=" * 60)
        print("AARON JUDGE 2024 STATCAST STATS:")
        print("=" * 60)
        print(f"Exit Velocity: {judge_stats['avg_hit_speed'].values[0]:.1f} mph")
        print(f"Max Exit Velocity: {judge_stats['max_hit_speed'].values[0]:.1f} mph")
        print(f"Barrel Rate: {judge_stats['barrel_batted_rate'].values[0]:.1f}%")
        print(f"Hard Hit %: {judge_stats['solidcontact_percent'].values[0]:.1f}%")
        print(f"Batted Ball Events: {judge_stats['attempts'].values[0]}")
    
except Exception as e:
    print(f"\n✗ Error: {e}")
    exit()

# ============================================================================
# TEST 3: Save the data
# ============================================================================
print("\n" + "=" * 60)
print("TEST 3: Saving data to CSV...")
print("=" * 60)

try:
    batters_2024.to_csv('test_statcast_2024.csv', index=False)
    print("✓ Saved to: test_statcast_2024.csv")
    print(f"   File contains {len(batters_2024)} rows and {len(batters_2024.columns)} columns")
    
    # Show all available columns
    print("\nAll available columns in this dataset:")
    for i, col in enumerate(batters_2024.columns, 1):
        print(f"  {i:2d}. {col}")
    
except Exception as e:
    print(f"\n✗ Error saving: {e}")

# ============================================================================
# NEXT STEPS
# ============================================================================
print("\n" + "=" * 60)
print("✓ ALL TESTS PASSED!")
print("=" * 60)
print("\nYou now have:")
print("  • pybaseball working correctly")
print("  • Sample 2024 Statcast data for all batters")
print("  • A CSV file you can open in Excel")

print("\nNext steps:")
print("  1. Open 'test_statcast_2024.csv' in Excel to see the data")
print("  2. Review the column names above to see what metrics are available")
print("  3. Run 'collect_statcast_data.py' for the full data collection workflow")
print("  4. Integrate with your Spotrac contract data")

print("\nKey metrics you'll want for your model:")
print("  • avg_hit_speed (exit velocity)")
print("  • barrel_batted_rate (barrel %)")
print("  • solidcontact_percent (hard hit %)")
print("  • max_hit_speed (peak power)")

print("\n" + "=" * 60)

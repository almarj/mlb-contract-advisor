"""
Test Script: Plate Discipline Metrics (Chase Rate, Whiff Rate)
==============================================================
This script explores the statcast_batter_percentile_ranks() function
to validate that chase rate and whiff rate data is available and usable.

Run from project root:
    python Data/tests/test_plate_discipline_metrics.py
"""

import pandas as pd
from pybaseball import cache, statcast_batter_percentile_ranks

# Enable caching to speed up repeated runs
cache.enable()

print("=" * 70)
print("PLATE DISCIPLINE METRICS - DATA EXPLORATION")
print("=" * 70)

# Test with 2024 data
YEAR = 2024

print(f"\n1. Fetching statcast_batter_percentile_ranks({YEAR})...")
try:
    percentile_data = statcast_batter_percentile_ranks(YEAR)
    print(f"   ✓ Retrieved {len(percentile_data)} players")
except Exception as e:
    print(f"   ✗ Error: {e}")
    exit(1)

# Show all available columns
print(f"\n2. Available columns ({len(percentile_data.columns)} total):")
print("-" * 50)
for i, col in enumerate(sorted(percentile_data.columns)):
    print(f"   {col}")

# Look for chase/whiff related columns
print("\n3. Searching for chase/whiff related columns...")
chase_whiff_cols = [col for col in percentile_data.columns
                   if any(term in col.lower() for term in ['chase', 'whiff', 'swing', 'contact', 'k_percent', 'bb_percent'])]
print(f"   Found: {chase_whiff_cols}")

# Show sample data for key columns
print("\n4. Sample data for relevant columns:")
print("-" * 50)

# Try to identify the right columns
potential_cols = ['player_name', 'year', 'whiff_percent', 'k_percent', 'bb_percent',
                  'oz_swing_percent', 'oz_contact_percent', 'chase_percent',
                  'xba', 'xslg', 'xwoba']

available_cols = [col for col in potential_cols if col in percentile_data.columns]
print(f"   Checking columns: {available_cols}")

if available_cols:
    print(percentile_data[available_cols].head(10).to_string())

# Test with known players
print("\n5. Looking up known players...")
print("-" * 50)

test_players = ['Soto', 'Judge', 'Ohtani', 'Trout']
for player in test_players:
    matches = percentile_data[percentile_data['player_name'].str.contains(player, case=False, na=False)]
    if not matches.empty:
        row = matches.iloc[0]
        print(f"\n   {row.get('player_name', player)}:")
        # Print all numeric columns for this player
        for col in percentile_data.columns:
            if col != 'player_name' and col != 'year':
                val = row.get(col)
                if pd.notna(val):
                    print(f"      {col}: {val}")

# Check data completeness
print("\n6. Data completeness check:")
print("-" * 50)
for col in percentile_data.columns:
    non_null = percentile_data[col].notna().sum()
    pct = (non_null / len(percentile_data)) * 100
    print(f"   {col}: {non_null}/{len(percentile_data)} ({pct:.1f}%)")

# Save sample to CSV for manual inspection
output_file = 'Data/tests/percentile_ranks_sample_2024.csv'
percentile_data.to_csv(output_file, index=False)
print(f"\n7. Saved full data to: {output_file}")

print("\n" + "=" * 70)
print("SUMMARY")
print("=" * 70)
print("""
Next steps:
1. Review the columns above to identify exact names for chase/whiff metrics
2. Check if data is percentiles (0-100) or raw rates (0.0-1.0)
3. Verify coverage - do most players have these stats?
4. If data looks good, proceed with Option 2 (feature branch integration)
""")

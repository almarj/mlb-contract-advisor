"""
Quick Data Analysis - MLB Contract Advisor
Visualize the relationship between player performance and contract value
"""

import pandas as pd
import matplotlib.pyplot as plt

print("=" * 70)
print("MLB CONTRACT ADVISOR - QUICK DATA ANALYSIS")
print("=" * 70)

# Load your master dataset
print("\nLoading data...")
df = pd.read_csv('master_contract_dataset.csv')
print(f"✓ Loaded {len(df)} contracts")

# Separate batters and pitchers
batters = df[df['wRC_plus_3yr'].notna()]
pitchers = df[df['ERA_3yr'].notna()]

print(f"\nDataset breakdown:")
print(f"  Batters: {len(batters)}")
print(f"  Pitchers: {len(pitchers)}")

# ============================================================================
# PLOT 1: WAR vs AAV (All Players)
# ============================================================================
print("\n[1] Creating WAR vs AAV plot (all players)...")

plt.figure(figsize=(10, 6))
plt.scatter(df['WAR_3yr'], df['AAV']/1000000, alpha=0.6, s=100)
plt.xlabel('3-Year Average WAR', fontsize=12)
plt.ylabel('AAV (Millions $)', fontsize=12)
plt.title('Player Value (WAR) vs Contract Size (AAV)', fontsize=14, fontweight='bold')
plt.grid(True, alpha=0.3)

# Add a trend line
import numpy as np
z = np.polyfit(df['WAR_3yr'], df['AAV']/1000000, 1)
p = np.poly1d(z)
plt.plot(df['WAR_3yr'], p(df['WAR_3yr']), "r--", alpha=0.8, linewidth=2, label='Trend')
plt.legend()

plt.tight_layout()
plt.savefig('1_war_vs_aav_all.png', dpi=300)
print("✓ Saved: 1_war_vs_aav_all.png")

# ============================================================================
# PLOT 2: WAR vs AAV (Batters Only, colored by position)
# ============================================================================
print("[2] Creating WAR vs AAV plot (batters only)...")

plt.figure(figsize=(12, 6))

# Group by position for color coding
positions = batters['position'].unique()
colors = plt.cm.tab10(range(len(positions)))

for i, pos in enumerate(positions):
    pos_data = batters[batters['position'] == pos]
    plt.scatter(pos_data['WAR_3yr'], pos_data['AAV']/1000000, 
               label=pos, alpha=0.7, s=100, color=colors[i])

plt.xlabel('3-Year Average WAR', fontsize=12)
plt.ylabel('AAV (Millions $)', fontsize=12)
plt.title('Batter Value (WAR) vs Contract Size by Position', fontsize=14, fontweight='bold')
plt.grid(True, alpha=0.3)
plt.legend(title='Position', bbox_to_anchor=(1.05, 1), loc='upper left')

plt.tight_layout()
plt.savefig('2_war_vs_aav_batters.png', dpi=300, bbox_inches='tight')
print("✓ Saved: 2_war_vs_aav_batters.png")

# ============================================================================
# PLOT 3: Exit Velocity vs AAV (Statcast data)
# ============================================================================
print("[3] Creating Exit Velocity vs AAV plot...")

batters_statcast = batters[batters['avg_exit_velo'].notna()]

plt.figure(figsize=(10, 6))
scatter = plt.scatter(batters_statcast['avg_exit_velo'], 
                     batters_statcast['AAV']/1000000,
                     c=batters_statcast['WAR_3yr'], 
                     cmap='viridis', 
                     alpha=0.7, 
                     s=100)
plt.colorbar(scatter, label='3-Year WAR')
plt.xlabel('Average Exit Velocity (mph)', fontsize=12)
plt.ylabel('AAV (Millions $)', fontsize=12)
plt.title('Exit Velocity vs Contract Size (colored by WAR)', fontsize=14, fontweight='bold')
plt.grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig('3_exit_velo_vs_aav.png', dpi=300)
print("✓ Saved: 3_exit_velo_vs_aav.png")

# ============================================================================
# PLOT 4: ERA vs AAV (Pitchers)
# ============================================================================
print("[4] Creating ERA vs AAV plot (pitchers)...")

plt.figure(figsize=(10, 6))
plt.scatter(pitchers['ERA_3yr'], pitchers['AAV']/1000000, alpha=0.7, s=100, color='red')
plt.xlabel('3-Year Average ERA', fontsize=12)
plt.ylabel('AAV (Millions $)', fontsize=12)
plt.title('Pitcher ERA vs Contract Size (lower ERA = better)', fontsize=14, fontweight='bold')
plt.grid(True, alpha=0.3)

# ERA is inverse - lower is better
plt.gca().invert_xaxis()

plt.tight_layout()
plt.savefig('4_era_vs_aav_pitchers.png', dpi=300)
print("✓ Saved: 4_era_vs_aav_pitchers.png")

# ============================================================================
# SUMMARY STATISTICS
# ============================================================================
print("\n" + "=" * 70)
print("SUMMARY STATISTICS")
print("=" * 70)

print("\nTop 10 Highest Paid Players:")
top_10 = df.nlargest(10, 'AAV')[['player_name', 'position', 'WAR_3yr', 'AAV', 'year_signed']]
top_10['AAV'] = top_10['AAV'] / 1000000  # Convert to millions
print(top_10.to_string(index=False))

print("\n\nTop 10 Best WAR per Dollar:")
df['WAR_per_million'] = df['WAR_3yr'] / (df['AAV'] / 1000000)
best_value = df.nlargest(10, 'WAR_per_million')[['player_name', 'position', 'WAR_3yr', 'AAV', 'WAR_per_million']]
best_value['AAV'] = best_value['AAV'] / 1000000
print(best_value.to_string(index=False))

print("\n\nCorrelation Analysis:")
print(f"WAR vs AAV correlation: {df['WAR_3yr'].corr(df['AAV']):.3f}")
if len(batters_statcast) > 0:
    print(f"Exit Velocity vs AAV correlation: {batters_statcast['avg_exit_velo'].corr(batters_statcast['AAV']):.3f}")

print("\n" + "=" * 70)
print("ANALYSIS COMPLETE!")
print("=" * 70)
print("\nCreated 4 visualizations:")
print("  1. 1_war_vs_aav_all.png - Overall relationship")
print("  2. 2_war_vs_aav_batters.png - Batters by position")
print("  3. 3_exit_velo_vs_aav.png - Statcast exit velocity")
print("  4. 4_era_vs_aav_pitchers.png - Pitcher performance")
print("\nOpen these images to see your data patterns!")
print("=" * 70)

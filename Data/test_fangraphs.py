from pybaseball import cache, batting_stats

# Enable caching (important!)
cache.enable()

print("Getting 2024 batting data from FanGraphs...")

# Get 2024 batting stats
batting_2024 = batting_stats(2024, 2024)

print(f"Success! Downloaded {len(batting_2024)} players")
print(f"Total columns: {len(batting_2024.columns)}")

# Show first 5 players
print("\nFirst 5 players:")
print(batting_2024[['Name', 'Team', 'WAR', 'wRC+', 'HR']].head())

# Save it
batting_2024.to_csv('test_2024_batting.csv', index=False)
print("\nSaved to: test_2024_batting.csv")

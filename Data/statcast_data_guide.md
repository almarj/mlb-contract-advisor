# Statcast Data Collection Guide for MLB Contract Advisor

## Overview
This guide helps you collect the Statcast metrics needed for your contract prediction model. Your PRD mentions using metrics like exit velocity, barrel rate, sprint speed, and OAA (Outs Above Average) as optional features to improve prediction accuracy.

## What Data You Need

Based on your PRD (Section 5.2), you need:

### Required Metrics (from FanGraphs/Baseball Reference):
- **WAR** (Wins Above Replacement) - 3-year average
- **wRC+** (for position players) - normalized batting performance
- **ERA+** (for pitchers) - normalized pitching performance

### Optional Statcast Metrics (improve accuracy):
- **Exit Velocity** (avg_hit_speed)
- **Barrel Rate** (barrel%)
- **Sprint Speed** (sprint_speed)
- **OAA** (Outs Above Average for fielders)
- **Hard Hit %** (hard_hit%)
- **Launch Angle** (avg_launch_angle)

## Timeline: What Data Is Available When

**Important:** Statcast data availability varies by metric:
- **2008-2014**: Basic PITCHf/x data only (pitch tracking)
- **2015-present**: Full Statcast including exit velocity, launch angle, barrels, sprint speed
- **2020-present**: Enhanced fielding metrics (OAA)

**For your project:** Focus on 2015+ data since that's when the key batting metrics became available.

## Step-by-Step Data Collection Process

### Step 1: Install pybaseball
```bash
pip install pybaseball
```

### Step 2: Understand the Data Structure

You'll need to collect data at two different aggregation levels:

1. **Season-level aggregated data** - Easiest for most metrics
   - Use for: Exit velocity, barrel rate, hard hit %, sprint speed
   - Function: `statcast_batter_exitvelo_barrels(year)`

2. **Player career averages** - For training your model
   - Aggregate multiple seasons to get 3-year averages
   - Match to contract signing year

### Step 3: Key Functions You'll Use

#### For Position Players (Batters):
```python
from pybaseball import statcast_batter_exitvelo_barrels
from pybaseball import statcast_batter_expected_stats
from pybaseball import statcast_batter_percentile_ranks

# Exit velocity, barrels, hard hit % - available from 2015+
batters_2024 = statcast_batter_exitvelo_barrels(2024)

# Expected stats (xBA, xSLG, xwOBA) - also useful
expected_2024 = statcast_batter_expected_stats(2024)

# Percentile ranks - includes sprint speed
percentiles_2024 = statcast_batter_percentile_ranks(2024)
```

#### For Pitchers:
```python
from pybaseball import statcast_pitcher_exitvelo_barrels
from pybaseball import statcast_pitcher_expected_stats

# Batted ball data against (exit velo allowed, barrels allowed)
pitchers_2024 = statcast_pitcher_exitvelo_barrels(2024)

# Expected stats allowed
expected_2024 = statcast_pitcher_expected_stats(2024)
```

## Important Data Columns

When you pull `statcast_batter_exitvelo_barrels()`, you'll get columns like:
- `last_name`, `first_name`, `player_id`
- `attempts` - number of batted ball events
- `avg_hit_speed` - average exit velocity
- `avg_hit_angle` - average launch angle
- `max_hit_speed` - max exit velocity
- `avg_distance` - average hit distance
- `barrel_batted_rate` - barrel % (key metric!)
- `solidcontact_percent` - hard hit %
- `flareburner_percent`
- `poorlyunder_percent`
- `poorlytopped_percent`
- `poorlyweak_percent`

When you pull `statcast_batter_percentile_ranks()`, you'll get:
- `sprint_speed` - sprint speed in ft/sec
- Percentile versions of many metrics

## Workflow for Your Project

### Phase 0: Data Collection (Weeks 1-2)

**Goal:** Build a dataset with contract data + player stats for 2015-2025

```
For each player who signed a contract:
  1. Get contract details from Spotrac (AAV, length, year signed, age)
  2. Get their stats from the year BEFORE they signed
  3. Calculate 3-year averages (if available)
  4. Merge Statcast metrics for that year
  5. Store in your PostgreSQL database
```

### Data Collection Strategy:

1. **Start with contracts (Spotrac)**: 500-800 contracts from 2015-2025
2. **Get player IDs**: Use `playerid_lookup()` to match names to IDs
3. **Pull stats year-by-year**: Loop through 2015-2024, collecting metrics
4. **Join datasets**: Match contract signing year to player stats
5. **Calculate 3-year averages**: Average WAR, wRC+, exit velo, etc. over prior 3 years

## Sample Workflow Code Structure

```python
# Pseudo-code for your data pipeline

import pandas as pd
from pybaseball import playerid_lookup, statcast_batter_exitvelo_barrels

# 1. Load your contract data from Spotrac
contracts = pd.read_csv('spotrac_contracts.csv')
# Columns: player_name, position, year_signed, age_at_signing, AAV, length

# 2. Get player IDs
def get_player_id(last_name, first_name):
    result = playerid_lookup(last_name, first_name)
    if len(result) > 0:
        return result.iloc[0]['key_mlbam']
    return None

contracts['player_id'] = contracts.apply(
    lambda row: get_player_id(row['last_name'], row['first_name']), 
    axis=1
)

# 3. Pull Statcast data for each year
all_statcast_data = {}
for year in range(2015, 2026):
    print(f"Pulling {year} data...")
    all_statcast_data[year] = statcast_batter_exitvelo_barrels(year)

# 4. For each contract, get stats from year BEFORE signing
def get_player_stats_before_signing(player_id, year_signed):
    stats_year = year_signed - 1  # Get previous year's stats
    if stats_year in all_statcast_data:
        player_stats = all_statcast_data[stats_year][
            all_statcast_data[stats_year]['player_id'] == player_id
        ]
        return player_stats
    return None

# 5. Merge and create final dataset
# ... continue with merging logic
```

## Key Considerations

### 1. **Missing Data**
- Not all players have Statcast data (especially pre-2015)
- Not all players meet minimum batted ball event thresholds
- Handle missing values in your model (use median/mean imputation or drop features)

### 2. **Position Players vs Pitchers**
- Use different functions for each
- Position players: focus on batting metrics
- Pitchers: focus on batted ball allowed, spin rate, velocity

### 3. **Data Quality**
Your PRD mentions:
- Quality score: ≥ 95%
- Completeness: 100% required fields, 80%+ desirable fields

**Recommendation:** Make Statcast metrics optional features. Your model should work without them but be more accurate with them.

### 4. **Free Agents vs Extensions**
- Free agents: Use stats from most recent season
- Extensions: Use current season stats (they're still playing)

## Next Steps

1. **Start simple**: First get just exit velocity and barrel rate for 2024 free agents
2. **Test the data**: Make sure you can match player names to IDs
3. **Expand backwards**: Once 2024 works, loop through 2015-2023
4. **Calculate 3-year averages**: For each player at signing time
5. **Store in database**: Create your PostgreSQL tables with this data

## Helpful Resources

- **pybaseball docs**: https://github.com/jldbc/pybaseball/tree/master/docs
- **Baseball Savant column definitions**: https://baseballsavant.mlb.com/csv-docs
- **Statcast leaderboards** (to verify your data): https://baseballsavant.mlb.com/statcast_search

## Common Pitfalls to Avoid

1. **Don't pull pitch-by-pitch data** - You want aggregated season stats, not 700k+ pitches
2. **Enable caching** - Add `pybaseball.cache.enable()` at the start of your script
3. **Rate limits** - Baseball Savant has limits; use caching and avoid rapid repeated queries
4. **Player ID matching** - Some players have multiple IDs; validate your matches
5. **Qualified vs unqualified players** - Functions default to qualified players; you may need to lower minimums

## Questions to Consider

As you build this:
- Do you want Statcast data for ALL 500-800 contracts, or just recent ones (2020+)?
- Should the model handle missing Statcast gracefully (recommended: yes)
- Do you need defensive metrics (OAA) for all positions or just premium defensive positions?

Let me know if you'd like me to create the actual Python script for data collection!

# Statcast Data Collection - Frequently Asked Questions

## General Questions

### Q: What's the difference between Statcast data and traditional stats?

**Traditional stats** (available on Baseball Reference, FanGraphs):
- Batting average, home runs, RBIs, ERA, wins, strikeouts
- **WAR** (Wins Above Replacement) - comprehensive value metric
- **wRC+** / **ERA+** - park and league-adjusted stats
- Available going back to 1800s

**Statcast data** (available on Baseball Savant via pybaseball):
- How hard the ball was hit (exit velocity)
- What angle it was hit (launch angle)
- How fast the player runs (sprint speed)
- Defensive positioning and range (OAA)
- Available from 2008+ (most useful metrics from 2015+)

### Q: Do I need BOTH types of data for my model?

**Yes, ideally.** Your PRD lists:
- **Required**: WAR, wRC+, ERA+ (from FanGraphs/Baseball Reference)
- **Optional but improves accuracy**: Exit velocity, barrel rate, sprint speed, OAA (from Statcast)

Think of it this way:
- Traditional stats = what happened (results)
- Statcast = how it happened (quality of contact)

### Q: Can my model work without Statcast data?

**Yes!** Your BRD mentions 72% accuracy on 2024 free agents. You can definitely build a working model with just:
- Age
- Position
- WAR (3-year average)
- wRC+ or ERA+
- Contract market trends (year signed)

Statcast data just makes it better by adding:
- Exit velocity → predicts future power
- Barrel rate → predicts sustainable batting success
- Sprint speed → aging curve indicator

## Data Availability Questions

### Q: Why does my data only go back to 2015?

**Exit velocity and launch angle** (the most useful Statcast metrics) are only available from 2015 onwards. Before 2015, MLB used PITCHf/x which only tracked pitches, not batted balls.

Timeline:
- **2008-2014**: PITCHf/x (pitch tracking only)
- **2015-present**: Full Statcast (batted ball tracking)
- **2020-present**: Enhanced fielding metrics (OAA)

**For your project**: Focus on 2015-2025 contracts to maximize Statcast availability.

### Q: Some players are missing from my Statcast data. Why?

Common reasons:
1. **Didn't reach minimum batted ball events** - Default is "qualified" players (usually ~400 PA). Lower the `minBBE` parameter if needed.
2. **Player debuted after 2015** - No historical Statcast data exists
3. **Pitcher** - You need different functions for pitchers vs batters
4. **Name spelling mismatch** - Try variations or check the player ID manually

### Q: What does "qualified" mean?

A **qualified player** has enough plate appearances to appear in official league leaderboards:
- **Batters**: ~502 PA (3.1 PA per team game)
- **Pitchers**: ~162 IP (1 IP per team game)

For your model, you might want to lower these minimums since:
- Some contract signings happen for part-time players
- Injuries affect playing time
- You need more training data

## Technical Questions

### Q: How do I handle missing Statcast data for pre-2015 contracts?

**Option 1** (Recommended): Make Statcast features optional
```python
# If statcast data exists, use it; if not, leave as null
model_features = [
    'age', 'position', 'WAR_3yr', 'wRC+',  # Always available
    'exit_velo', 'barrel_rate'  # Optional - will be null for pre-2015
]

# Most ML models (including XGBoost) can handle missing values
```

**Option 2**: Only train on 2015+ contracts
- Smaller dataset but complete features
- Still get 9-10 years of data (2015-2024)

**Option 3**: Create separate models
- One model for pre-2015 (no Statcast)
- One model for 2015+ (with Statcast)

### Q: What's the difference between `statcast_batter_exitvelo_barrels()` and `statcast()`?

**`statcast()`** - Pitch-by-pitch raw data
- Returns 700,000+ rows per season
- Every single pitch thrown in MLB
- Used for deep-dive analysis
- **You probably don't need this**

**`statcast_batter_exitvelo_barrels()`** - Season aggregated stats
- Returns ~300-500 rows (one per player)
- Averaged metrics for the season
- Exit velo, barrel rate, hard hit %, etc.
- **This is what you want**

### Q: Do I need to download data every time I run my script?

**No!** Use caching:
```python
from pybaseball import cache
cache.enable()  # Add this at the top of your script
```

After first download, data is stored locally. Subsequent runs are instant.

### Q: How long does it take to download all the data?

**First time** (without cache):
- Single year (e.g., 2024): 30-60 seconds
- Multiple years (2015-2024): 5-10 minutes
- FanGraphs data (2015-2024): 2-3 minutes
- **Total for full dataset**: 10-15 minutes

**With cache enabled**:
- Subsequent runs: < 5 seconds

## Data Integration Questions

### Q: How do I match Spotrac contracts to player stats?

**Step-by-step**:
1. Load your Spotrac contract data (name, year signed, AAV, etc.)
2. Use `playerid_lookup()` to get MLBAM IDs for each player
3. Pull stats for the year BEFORE they signed
4. Match on player_id
5. Calculate 3-year averages if needed

Example:
```python
# Player signed in 2023
# Use 2022 stats (most recent full season before signing)
# Ideally: average 2020, 2021, 2022 for 3-year average
```

### Q: Should I use stats from the year they signed or the year before?

**Use the year BEFORE signing** for most contracts:
- Free agents sign in offseason (Nov-Feb) based on prior season
- Example: Player signs in Jan 2023 → use 2022 stats

**Exception - Extensions**: 
- Player extends during the season
- Use current season stats (partial year) or prior full year

### Q: What if a player's stats change significantly year-to-year?

This is actually valuable information! Options:
1. **Use 3-year average** - Smooths out fluctuations (recommended in your PRD)
2. **Add recency weighting** - Weight recent year higher (60% recent, 40% older)
3. **Include variance as a feature** - "consistency score"

### Q: How do I calculate 3-year averages?

```python
# Pseudo-code
player_stats_2020 = get_stats(player_id, 2020)
player_stats_2021 = get_stats(player_id, 2021)
player_stats_2022 = get_stats(player_id, 2022)

WAR_3yr_avg = (WAR_2020 + WAR_2021 + WAR_2022) / 3
exit_velo_3yr_avg = (EV_2020 + EV_2021 + EV_2022) / 3
```

Handle missing years gracefully (injuries, callups, etc.)

## Model-Specific Questions

### Q: Which Statcast metrics matter most for contract prediction?

Based on baseball analytics research:

**For Hitters**:
1. **Exit velocity** - Strong predictor of future performance
2. **Barrel rate** - Predictive of power and batting average
3. **Sprint speed** - Indicator of age-related decline
4. **Hard hit %** - Quality of contact

**For Pitchers**:
1. **Exit velocity allowed** - Pitching quality
2. **Barrel rate allowed** - Avoiding hard contact
3. **Spin rate** - Pitch effectiveness (for starting pitchers)

**For All Players**:
- **WAR** is still the single best metric
- Statcast metrics help predict future WAR changes

### Q: Should I normalize/standardize Statcast metrics?

**Yes, for model training:**
- Exit velocity: Scale to 0-1 or z-scores
- Barrel rate: Already in %, may not need scaling
- WAR: Definitely scale (varies widely)

**XGBoost** (your chosen algorithm) is relatively robust to different scales, but it still helps.

### Q: What minimum sample size do I need for Statcast metrics?

Baseball Savant defaults:
- **Qualified batters**: ~400 PA
- **Minimum useful**: 100+ batted ball events

**For your model**:
- Set `minBBE=100` to get more players
- Add a "reliability" feature based on sample size
- Weight predictions based on confidence

## Troubleshooting

### Q: I'm getting "BrokenProcessPool" errors

Add this to your script:
```python
if __name__ == "__main__":
    # Your code here
    main()
```

Windows/Mac require this for multiprocessing.

### Q: The data looks different than Baseball Savant website

- Website shows **qualified** players by default
- API returns what you specify via `minBBE` or `minPA`
- Try lowering minimums to see more players

### Q: How do I verify my data is correct?

1. **Spot check**: Look up a player manually on Baseball Savant
2. **Compare counts**: Number of qualified players should match leaderboards
3. **Sanity check ranges**: Exit velo usually 85-95 mph, barrels 5-20%
4. **Check for duplicates**: Each player should appear once per season

### Q: Some player names don't match between Spotrac and pybaseball

Common issues:
- Abbreviations: "Alex" vs "Alexander"
- Accented characters: "José" vs "Jose"
- Jr./Sr. suffixes
- Traded players (multiple team listings)

**Solution**: Use player IDs, not names, for matching after initial lookup.

## Next Steps

### Q: I have my Statcast data. Now what?

1. **Merge with contract data**: Match on player_id and year
2. **Calculate 3-year averages**: Smooth out year-to-year variance
3. **Handle missing values**: Decide on imputation strategy
4. **Feature engineering**: Create derived features (age^2, WAR * position adjustment)
5. **Store in database**: PostgreSQL tables per your PRD
6. **Begin model training**: Feed into XGBoost

### Q: Where can I get help if stuck?

- **pybaseball GitHub**: https://github.com/jldbc/pybaseball/issues
- **Baseball Savant**: https://baseballsavant.mlb.com/csv-docs
- **This project's Discord/Slack**: [If you set one up for beta testers]

### Q: Can I see what the final dataset should look like?

**Ideal structure** for model training:

| player_name | position | year_signed | age | WAR_3yr | wRC+ | exit_velo | barrel_rate | AAV | length |
|-------------|----------|-------------|-----|---------|------|-----------|-------------|-----|--------|
| Aaron Judge | OF       | 2023        | 30  | 7.2     | 158  | 95.3      | 15.8        | 40M | 9      |
| Mookie Betts| OF       | 2020        | 27  | 8.4     | 151  | 94.1      | 14.2        | 30M | 12     |

Where:
- `AAV` and `length` are your **target variables** (what you're predicting)
- Everything else is **features** (inputs to the model)

---

**Still have questions?** Check the main guide (`statcast_data_guide.md`) or the sample scripts!

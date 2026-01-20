"""
Seed the database with contract and player data from the master dataset,
plus prospects from FanGraphs data.
"""
import sys
import os

# Add app to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pandas as pd
import numpy as np
from pathlib import Path
from app.models.database import engine, Base, Contract, Player, PlayerYearlyStats, SessionLocal
from app.config import MASTER_DATA_DIR
from app.utils import normalize_name as _normalize_name, PITCHER_POSITIONS

# Statcast data cache (loaded once)
BATTER_STATCAST_CACHE = {}
PITCHER_STATCAST_CACHE = {}

# Path to FanGraphs data (one level up from backend)
FANGRAPHS_DATA_DIR = Path(__file__).parent.parent / "Data"


def normalize_name(name):
    """
    Normalize player names for matching.
    Wrapper around shared utils function that handles pandas NA values.
    """
    if pd.isna(name):
        return ""
    return _normalize_name(str(name))


def calculate_3yr_avg_batter(player_seasons: pd.DataFrame) -> dict:
    """Calculate 3-year average stats for a batter from their season data."""
    # Get most recent 3 seasons
    recent = player_seasons.nlargest(3, 'Season')

    return {
        'war_3yr': recent['WAR'].mean() if 'WAR' in recent.columns else None,
        'wrc_plus_3yr': recent['wRC+'].mean() if 'wRC+' in recent.columns else None,
        'avg_3yr': recent['AVG'].mean() if 'AVG' in recent.columns else None,
        'obp_3yr': recent['OBP'].mean() if 'OBP' in recent.columns else None,
        'slg_3yr': recent['SLG'].mean() if 'SLG' in recent.columns else None,
        'hr_3yr': recent['HR'].mean() if 'HR' in recent.columns else None,
        'current_age': int(recent.iloc[0]['Age']) if 'Age' in recent.columns else None,
        'last_season': int(recent['Season'].max()),
        'team': recent.iloc[0]['Team'] if 'Team' in recent.columns else None,
    }


def calculate_3yr_avg_pitcher(player_seasons: pd.DataFrame) -> dict:
    """Calculate 3-year average stats for a pitcher from their season data."""
    # Get most recent 3 seasons
    recent = player_seasons.nlargest(3, 'Season')

    # Determine if starter based on GS/G ratio
    if 'GS' in recent.columns and 'G' in recent.columns:
        gs = recent['GS'].sum()
        g = recent['G'].sum()
        is_starter = (gs / max(g, 1)) > 0.5
    else:
        is_starter = True

    return {
        'war_3yr': recent['WAR'].mean() if 'WAR' in recent.columns else None,
        'era_3yr': recent['ERA'].mean() if 'ERA' in recent.columns else None,
        'fip_3yr': recent['FIP'].mean() if 'FIP' in recent.columns else None,
        'k_9_3yr': recent['K/9'].mean() if 'K/9' in recent.columns else None,
        'bb_9_3yr': recent['BB/9'].mean() if 'BB/9' in recent.columns else None,
        'ip_3yr': recent['IP'].mean() if 'IP' in recent.columns else None,
        'current_age': int(recent.iloc[0]['Age']) if 'Age' in recent.columns else None,
        'last_season': int(recent['Season'].max()),
        'team': recent.iloc[0]['Team'] if 'Team' in recent.columns else None,
        'is_starter': is_starter,
    }


def calculate_recent_stats_batter(player_name: str, batting_df: pd.DataFrame, years: list) -> dict:
    """
    Calculate recent 3-year stats for a batter.
    Returns None values if player not found or insufficient data.
    """
    norm_name = normalize_name(player_name)
    player_seasons = batting_df[batting_df['_normalized_name'] == norm_name]

    if len(player_seasons) == 0:
        return {}

    # Filter to recent years
    recent = player_seasons[player_seasons['Season'].isin(years)]

    if len(recent) == 0:
        return {}

    return {
        'recent_war_3yr': recent['WAR'].mean() if 'WAR' in recent.columns else None,
        'recent_wrc_plus_3yr': recent['wRC+'].mean() if 'wRC+' in recent.columns else None,
        'recent_avg_3yr': recent['AVG'].mean() if 'AVG' in recent.columns else None,
        'recent_obp_3yr': recent['OBP'].mean() if 'OBP' in recent.columns else None,
        'recent_slg_3yr': recent['SLG'].mean() if 'SLG' in recent.columns else None,
        'recent_hr_3yr': recent['HR'].mean() if 'HR' in recent.columns else None,
    }


def calculate_recent_stats_pitcher(player_name: str, pitching_df: pd.DataFrame, years: list) -> dict:
    """
    Calculate recent 3-year stats for a pitcher.
    Returns None values if player not found or insufficient data.
    """
    norm_name = normalize_name(player_name)
    player_seasons = pitching_df[pitching_df['_normalized_name'] == norm_name]

    if len(player_seasons) == 0:
        return {}

    # Filter to recent years
    recent = player_seasons[player_seasons['Season'].isin(years)]

    if len(recent) == 0:
        return {}

    return {
        'recent_war_3yr': recent['WAR'].mean() if 'WAR' in recent.columns else None,
        'recent_era_3yr': recent['ERA'].mean() if 'ERA' in recent.columns else None,
        'recent_fip_3yr': recent['FIP'].mean() if 'FIP' in recent.columns else None,
        'recent_k_9_3yr': recent['K/9'].mean() if 'K/9' in recent.columns else None,
        'recent_bb_9_3yr': recent['BB/9'].mean() if 'BB/9' in recent.columns else None,
        'recent_ip_3yr': recent['IP'].mean() if 'IP' in recent.columns else None,
    }


def load_statcast_data():
    """Load Statcast percentile data from pybaseball for recent years."""
    global BATTER_STATCAST_CACHE, PITCHER_STATCAST_CACHE

    try:
        from pybaseball import statcast_batter_percentile_ranks, statcast_pitcher_percentile_ranks, cache
        cache.enable()
    except ImportError:
        print("Warning: pybaseball not installed, skipping Statcast data")
        return False

    # Load recent years (2023-2025 for prospects)
    years_to_load = [2023, 2024, 2025]

    print("\nLoading Statcast percentile data...")
    for year in years_to_load:
        try:
            print(f"  Loading batter percentiles for {year}...", end='')
            BATTER_STATCAST_CACHE[year] = statcast_batter_percentile_ranks(year)
            print(f" ({len(BATTER_STATCAST_CACHE[year])} players)")
        except Exception as e:
            print(f" Error: {e}")

        try:
            print(f"  Loading pitcher percentiles for {year}...", end='')
            PITCHER_STATCAST_CACHE[year] = statcast_pitcher_percentile_ranks(year)
            print(f" ({len(PITCHER_STATCAST_CACHE[year])} pitchers)")
        except Exception as e:
            print(f" Error: {e}")

    return True


def get_batter_statcast(player_name: str, last_season: int) -> dict:
    """Get Statcast metrics for a batter from the most recent available year."""
    norm_name = normalize_name(player_name)

    # Try the last season first, then work backwards
    for year in [last_season, last_season - 1, last_season - 2]:
        if year not in BATTER_STATCAST_CACHE:
            continue

        df = BATTER_STATCAST_CACHE[year]
        if 'player_name' not in df.columns and 'last_name' in df.columns:
            # Build full name from first/last
            df = df.copy()
            df['player_name'] = df.get('first_name', '') + ' ' + df.get('last_name', '')

        # Match by name
        matches = df[df['player_name'].apply(lambda x: normalize_name(str(x)) if pd.notna(x) else '') == norm_name]

        if len(matches) == 0:
            # Try partial match on last name
            last_name = norm_name.split()[-1] if ' ' in norm_name else norm_name
            matches = df[df['player_name'].apply(
                lambda x: last_name in normalize_name(str(x)) if pd.notna(x) else False
            )]
            # Further filter by first name if multiple matches
            if len(matches) > 1:
                first_name = norm_name.split()[0] if ' ' in norm_name else ''
                if first_name:
                    matches = matches[matches['player_name'].apply(
                        lambda x: first_name in normalize_name(str(x)) if pd.notna(x) else False
                    )]

        if len(matches) > 0:
            row = matches.iloc[0]
            return {
                'avg_exit_velo': float(row['exit_velocity']) if 'exit_velocity' in row and pd.notna(row.get('exit_velocity')) else None,
                'barrel_rate': float(row['barrel']) if 'barrel' in row and pd.notna(row.get('barrel')) else None,
                'max_exit_velo': float(row['hard_hit']) if 'hard_hit' in row and pd.notna(row.get('hard_hit')) else None,  # Using hard_hit as proxy
                'hard_hit_pct': float(row['hard_hit']) if 'hard_hit' in row and pd.notna(row.get('hard_hit')) else None,
                'chase_rate': float(row['chase_percent']) if 'chase_percent' in row and pd.notna(row.get('chase_percent')) else None,
                'whiff_rate': float(row['whiff_percent']) if 'whiff_percent' in row and pd.notna(row.get('whiff_percent')) else None,
            }

    return {}


def get_pitcher_statcast(player_name: str, last_season: int) -> dict:
    """Get Statcast metrics for a pitcher from the most recent available year."""
    norm_name = normalize_name(player_name)

    # Try the last season first, then work backwards
    for year in [last_season, last_season - 1, last_season - 2]:
        if year not in PITCHER_STATCAST_CACHE:
            continue

        df = PITCHER_STATCAST_CACHE[year]
        if 'player_name' not in df.columns and 'last_name' in df.columns:
            df = df.copy()
            df['player_name'] = df.get('first_name', '') + ' ' + df.get('last_name', '')

        # Match by name
        matches = df[df['player_name'].apply(lambda x: normalize_name(str(x)) if pd.notna(x) else '') == norm_name]

        if len(matches) == 0:
            last_name = norm_name.split()[-1] if ' ' in norm_name else norm_name
            matches = df[df['player_name'].apply(
                lambda x: last_name in normalize_name(str(x)) if pd.notna(x) else False
            )]
            if len(matches) > 1:
                first_name = norm_name.split()[0] if ' ' in norm_name else ''
                if first_name:
                    matches = matches[matches['player_name'].apply(
                        lambda x: first_name in normalize_name(str(x)) if pd.notna(x) else False
                    )]

        if len(matches) > 0:
            row = matches.iloc[0]
            return {
                'fb_velocity': float(row['fb_velocity']) if 'fb_velocity' in row and pd.notna(row.get('fb_velocity')) else None,
                'fb_spin': float(row['fb_spin']) if 'fb_spin' in row and pd.notna(row.get('fb_spin')) else None,
                'xera': float(row['xera']) if 'xera' in row and pd.notna(row.get('xera')) else None,
                'k_percent': float(row['k_percent']) if 'k_percent' in row and pd.notna(row.get('k_percent')) else None,
                'bb_percent': float(row['bb_percent']) if 'bb_percent' in row and pd.notna(row.get('bb_percent')) else None,
                'whiff_percent_pitcher': float(row['whiff_percent']) if 'whiff_percent' in row and pd.notna(row.get('whiff_percent')) else None,
                'chase_percent_pitcher': float(row['chase_percent']) if 'chase_percent' in row and pd.notna(row.get('chase_percent')) else None,
            }

    return {}


def is_likely_extension(age: int, length: int) -> bool:
    """
    Determine if a contract is likely a pre-free agency extension.

    MLB free agency typically requires 6 years of service time.
    Most players debut around age 22-24, so FA hits around age 28-30.

    Heuristic: Age <= 25 AND length >= 6 years = likely extension
    These are team-friendly deals signed before hitting free agency.

    Note: Using 25 instead of 26 to avoid false positives like Juan Soto
    who signed as a true free agent at age 26.
    """
    return age <= 25 and length >= 6


def seed_contracts(db, df, batting_df=None, pitching_df=None):
    """Seed contracts table from master dataset with recent stats."""
    print(f"Seeding {len(df)} contracts...")

    # Recent years for calculating current performance (2023-2025)
    recent_years = [2023, 2024, 2025]

    extensions_count = 0
    recent_stats_count = 0

    for _, row in df.iterrows():
        age = int(row['age_at_signing'])
        length = int(row['length'])
        is_ext = is_likely_extension(age, length)
        position = row['position']
        player_name = row['player_name']

        if is_ext:
            extensions_count += 1

        # Calculate recent stats if FanGraphs data available
        recent_stats = {}
        if position in PITCHER_POSITIONS and pitching_df is not None:
            recent_stats = calculate_recent_stats_pitcher(player_name, pitching_df, recent_years)
        elif batting_df is not None:
            recent_stats = calculate_recent_stats_batter(player_name, batting_df, recent_years)

        if recent_stats:
            recent_stats_count += 1

        contract = Contract(
            player_name=player_name,
            position=position,
            signing_team=str(row['signing_team']) if pd.notna(row.get('signing_team')) else None,
            year_signed=int(row['year_signed']),
            age_at_signing=age,
            aav=float(row['AAV']),
            total_value=float(row['total_value']) if pd.notna(row.get('total_value')) else None,
            length=length,
            war_3yr=float(row['WAR_3yr']) if pd.notna(row.get('WAR_3yr')) else None,
            wrc_plus_3yr=float(row['wRC_plus_3yr']) if pd.notna(row.get('wRC_plus_3yr')) else None,
            avg_3yr=float(row['AVG_3yr']) if pd.notna(row.get('AVG_3yr')) else None,
            obp_3yr=float(row['OBP_3yr']) if pd.notna(row.get('OBP_3yr')) else None,
            slg_3yr=float(row['SLG_3yr']) if pd.notna(row.get('SLG_3yr')) else None,
            hr_3yr=float(row['HR_3yr']) if pd.notna(row.get('HR_3yr')) else None,
            era_3yr=float(row['ERA_3yr']) if pd.notna(row.get('ERA_3yr')) else None,
            fip_3yr=float(row['FIP_3yr']) if pd.notna(row.get('FIP_3yr')) else None,
            k_9_3yr=float(row['K_9_3yr']) if pd.notna(row.get('K_9_3yr')) else None,
            bb_9_3yr=float(row['BB_9_3yr']) if pd.notna(row.get('BB_9_3yr')) else None,
            ip_3yr=float(row['IP_3yr']) if pd.notna(row.get('IP_3yr')) else None,
            avg_exit_velo=float(row['avg_exit_velo']) if pd.notna(row.get('avg_exit_velo')) else None,
            barrel_rate=float(row['barrel_rate']) if pd.notna(row.get('barrel_rate')) else None,
            max_exit_velo=float(row['max_exit_velo']) if pd.notna(row.get('max_exit_velo')) else None,
            hard_hit_pct=float(row['hard_hit_pct']) if pd.notna(row.get('hard_hit_pct')) else None,
            chase_rate=float(row['chase_rate']) if pd.notna(row.get('chase_rate')) else None,
            whiff_rate=float(row['whiff_rate']) if pd.notna(row.get('whiff_rate')) else None,
            # Pitcher Statcast
            fb_velocity=float(row['fb_velocity']) if pd.notna(row.get('fb_velocity')) else None,
            fb_spin=float(row['fb_spin']) if pd.notna(row.get('fb_spin')) else None,
            xera=float(row['xera']) if pd.notna(row.get('xera')) else None,
            k_percent=float(row['k_percent']) if pd.notna(row.get('k_percent')) else None,
            bb_percent=float(row['bb_percent']) if pd.notna(row.get('bb_percent')) else None,
            whiff_percent_pitcher=float(row['whiff_percent_pitcher']) if pd.notna(row.get('whiff_percent_pitcher')) else None,
            chase_percent_pitcher=float(row['chase_percent_pitcher']) if pd.notna(row.get('chase_percent_pitcher')) else None,
            is_extension=is_ext,
            # Recent performance stats
            recent_war_3yr=recent_stats.get('recent_war_3yr'),
            recent_wrc_plus_3yr=recent_stats.get('recent_wrc_plus_3yr'),
            recent_avg_3yr=recent_stats.get('recent_avg_3yr'),
            recent_obp_3yr=recent_stats.get('recent_obp_3yr'),
            recent_slg_3yr=recent_stats.get('recent_slg_3yr'),
            recent_hr_3yr=recent_stats.get('recent_hr_3yr'),
            recent_era_3yr=recent_stats.get('recent_era_3yr'),
            recent_fip_3yr=recent_stats.get('recent_fip_3yr'),
            recent_k_9_3yr=recent_stats.get('recent_k_9_3yr'),
            recent_bb_9_3yr=recent_stats.get('recent_bb_9_3yr'),
            recent_ip_3yr=recent_stats.get('recent_ip_3yr'),
        )
        db.add(contract)

    db.commit()
    print(f"Seeded {len(df)} contracts ({extensions_count} extensions, {recent_stats_count} with recent stats)")


def seed_signed_players(db, df):
    """Seed players table with signed players (has_contract=True)."""
    print("Seeding signed players...")

    # Get unique players
    unique_players = df.drop_duplicates(subset=['player_name', 'position'])

    for _, row in unique_players.iterrows():
        player = Player(
            name=row['player_name'],
            position=row['position'],
            team=None,
            is_pitcher=row['position'] in PITCHER_POSITIONS,
            has_contract=True,  # Mark as signed
        )
        db.add(player)

    db.commit()
    print(f"Seeded {len(unique_players)} signed players")
    return set(df['player_name'].apply(normalize_name).unique())


def seed_prospects(db, signed_player_names: set):
    """
    Seed prospects (unsigned players) from FanGraphs data.
    These are players who have stats but haven't signed FA contracts.
    """
    print("\nSeeding prospects from FanGraphs data...")

    batting_path = FANGRAPHS_DATA_DIR / "fangraphs_batting_2015-2025.csv"
    pitching_path = FANGRAPHS_DATA_DIR / "fangraphs_pitching_2015-2025.csv"

    if not batting_path.exists() or not pitching_path.exists():
        print("Warning: FanGraphs data files not found, skipping prospects")
        print(f"  Expected: {batting_path}")
        print(f"  Expected: {pitching_path}")
        return 0

    batting_df = pd.read_csv(batting_path)
    pitching_df = pd.read_csv(pitching_path)

    print(f"  Loaded {len(batting_df)} batting seasons")
    print(f"  Loaded {len(pitching_df)} pitching seasons")

    # Add normalized name column
    batting_df['_normalized_name'] = batting_df['Name'].apply(normalize_name)
    pitching_df['_normalized_name'] = pitching_df['Name'].apply(normalize_name)

    prospects_added = 0

    # Process batters
    print("  Processing batters...")
    unique_batters = batting_df['_normalized_name'].unique()

    for norm_name in unique_batters:
        # Skip if player has a contract
        if norm_name in signed_player_names:
            continue

        player_seasons = batting_df[batting_df['_normalized_name'] == norm_name]
        if len(player_seasons) == 0:
            continue

        # Calculate 3-year averages
        stats = calculate_3yr_avg_batter(player_seasons)

        # Get original name from most recent season
        original_name = player_seasons.sort_values('Season', ascending=False).iloc[0]['Name']

        # Skip if missing critical data
        if stats['war_3yr'] is None or stats['current_age'] is None:
            continue

        # Get Statcast data for this batter
        statcast = get_batter_statcast(original_name, stats['last_season'])

        player = Player(
            name=original_name,
            position="DH",  # Default for batters; user can change in form
            team=stats['team'],
            is_pitcher=False,
            has_contract=False,
            current_age=stats['current_age'],
            last_season=stats['last_season'],
            war_3yr=stats['war_3yr'],
            wrc_plus_3yr=stats['wrc_plus_3yr'],
            avg_3yr=stats['avg_3yr'],
            obp_3yr=stats['obp_3yr'],
            slg_3yr=stats['slg_3yr'],
            hr_3yr=stats['hr_3yr'],
            # Batter Statcast
            avg_exit_velo=statcast.get('avg_exit_velo'),
            barrel_rate=statcast.get('barrel_rate'),
            max_exit_velo=statcast.get('max_exit_velo'),
            hard_hit_pct=statcast.get('hard_hit_pct'),
            chase_rate=statcast.get('chase_rate'),
            whiff_rate=statcast.get('whiff_rate'),
        )
        db.add(player)
        prospects_added += 1

    # Process pitchers
    print("  Processing pitchers...")
    unique_pitchers = pitching_df['_normalized_name'].unique()

    for norm_name in unique_pitchers:
        # Skip if player has a contract
        if norm_name in signed_player_names:
            continue

        # Skip if already added as batter (avoid duplicates)
        if norm_name in unique_batters and norm_name not in signed_player_names:
            # Check if this is primarily a pitcher by IP
            pitcher_seasons = pitching_df[pitching_df['_normalized_name'] == norm_name]
            batter_seasons = batting_df[batting_df['_normalized_name'] == norm_name]

            # If they have more IP than PA, treat as pitcher
            total_ip = pitcher_seasons['IP'].sum() if 'IP' in pitcher_seasons.columns else 0
            total_pa = batter_seasons['PA'].sum() if 'PA' in batter_seasons.columns else 0

            if total_ip < total_pa * 0.5:  # Primarily a batter
                continue

        player_seasons = pitching_df[pitching_df['_normalized_name'] == norm_name]
        if len(player_seasons) == 0:
            continue

        # Calculate 3-year averages
        stats = calculate_3yr_avg_pitcher(player_seasons)

        # Get original name from most recent season
        original_name = player_seasons.sort_values('Season', ascending=False).iloc[0]['Name']

        # Skip if missing critical data
        if stats['war_3yr'] is None or stats['current_age'] is None:
            continue

        # Determine position (SP vs RP)
        position = "SP" if stats['is_starter'] else "RP"

        # Get Statcast data for this pitcher
        statcast = get_pitcher_statcast(original_name, stats['last_season'])

        player = Player(
            name=original_name,
            position=position,
            team=stats['team'],
            is_pitcher=True,
            has_contract=False,
            current_age=stats['current_age'],
            last_season=stats['last_season'],
            war_3yr=stats['war_3yr'],
            era_3yr=stats['era_3yr'],
            fip_3yr=stats['fip_3yr'],
            k_9_3yr=stats['k_9_3yr'],
            bb_9_3yr=stats['bb_9_3yr'],
            ip_3yr=stats['ip_3yr'],
            # Pitcher Statcast
            fb_velocity=statcast.get('fb_velocity'),
            fb_spin=statcast.get('fb_spin'),
            xera=statcast.get('xera'),
            k_percent=statcast.get('k_percent'),
            bb_percent=statcast.get('bb_percent'),
            whiff_percent_pitcher=statcast.get('whiff_percent_pitcher'),
            chase_percent_pitcher=statcast.get('chase_percent_pitcher'),
        )
        db.add(player)
        prospects_added += 1

    db.commit()
    print(f"  Seeded {prospects_added} prospects")
    return prospects_added


def seed_yearly_stats(db, batting_df=None, pitching_df=None):
    """
    Seed player yearly stats table for fast lookups when expanding contract rows.

    If CSV files are not available, fetches data from pybaseball.
    """
    print("\nSeeding yearly stats for fast lookups...")

    # If DataFrames not provided, try to fetch from pybaseball
    if batting_df is None or pitching_df is None:
        try:
            from pybaseball import batting_stats, pitching_stats, cache
            cache.enable()

            print("  Fetching batting stats from FanGraphs (this may take a few minutes)...")
            batting_df = batting_stats(2015, 2025, qual=50)
            batting_df['_normalized_name'] = batting_df['Name'].apply(normalize_name)
            print(f"    Downloaded {len(batting_df)} batting seasons")

            print("  Fetching pitching stats from FanGraphs...")
            pitching_df = pitching_stats(2015, 2025, qual=10)
            pitching_df['_normalized_name'] = pitching_df['Name'].apply(normalize_name)
            print(f"    Downloaded {len(pitching_df)} pitching seasons")

        except Exception as e:
            print(f"  Error fetching data from pybaseball: {e}")
            print("  Skipping yearly stats seeding - expand stats will use live API calls (slow)")
            return 0

    stats_added = 0

    # Process batting stats
    print("  Processing batting seasons...")
    for _, row in batting_df.iterrows():
        try:
            stat = PlayerYearlyStats(
                player_name=row['Name'],
                normalized_name=normalize_name(row['Name']),
                season=int(row['Season']),
                team=str(row.get('Team', '')) if pd.notna(row.get('Team')) else None,
                is_pitcher=False,
                games=int(row['G']) if 'G' in row and pd.notna(row.get('G')) else None,
                war=float(row['WAR']) if 'WAR' in row and pd.notna(row.get('WAR')) else None,
                pa=int(row['PA']) if 'PA' in row and pd.notna(row.get('PA')) else None,
                wrc_plus=float(row['wRC+']) if 'wRC+' in row and pd.notna(row.get('wRC+')) else None,
                avg=float(row['AVG']) if 'AVG' in row and pd.notna(row.get('AVG')) else None,
                obp=float(row['OBP']) if 'OBP' in row and pd.notna(row.get('OBP')) else None,
                slg=float(row['SLG']) if 'SLG' in row and pd.notna(row.get('SLG')) else None,
                hr=int(row['HR']) if 'HR' in row and pd.notna(row.get('HR')) else None,
                rbi=int(row['RBI']) if 'RBI' in row and pd.notna(row.get('RBI')) else None,
                runs=int(row['R']) if 'R' in row and pd.notna(row.get('R')) else None,
                hits=int(row['H']) if 'H' in row and pd.notna(row.get('H')) else None,
                sb=int(row['SB']) if 'SB' in row and pd.notna(row.get('SB')) else None,
            )
            db.add(stat)
            stats_added += 1
        except Exception as e:
            # Skip rows with bad data
            pass

    # Commit batters
    db.commit()
    print(f"    Added {stats_added} batting seasons")

    # Process pitching stats
    print("  Processing pitching seasons...")
    pitching_added = 0
    for _, row in pitching_df.iterrows():
        try:
            stat = PlayerYearlyStats(
                player_name=row['Name'],
                normalized_name=normalize_name(row['Name']),
                season=int(row['Season']),
                team=str(row.get('Team', '')) if pd.notna(row.get('Team')) else None,
                is_pitcher=True,
                games=int(row['G']) if 'G' in row and pd.notna(row.get('G')) else None,
                war=float(row['WAR']) if 'WAR' in row and pd.notna(row.get('WAR')) else None,
                wins=int(row['W']) if 'W' in row and pd.notna(row.get('W')) else None,
                losses=int(row['L']) if 'L' in row and pd.notna(row.get('L')) else None,
                era=float(row['ERA']) if 'ERA' in row and pd.notna(row.get('ERA')) else None,
                fip=float(row['FIP']) if 'FIP' in row and pd.notna(row.get('FIP')) else None,
                k_9=float(row['K/9']) if 'K/9' in row and pd.notna(row.get('K/9')) else None,
                bb_9=float(row['BB/9']) if 'BB/9' in row and pd.notna(row.get('BB/9')) else None,
                ip=float(row['IP']) if 'IP' in row and pd.notna(row.get('IP')) else None,
            )
            db.add(stat)
            pitching_added += 1
        except Exception as e:
            # Skip rows with bad data
            pass

    db.commit()
    print(f"    Added {pitching_added} pitching seasons")

    total_added = stats_added + pitching_added
    print(f"  Total yearly stats seeded: {total_added}")
    return total_added


def main():
    """Main seeding function."""
    print("=" * 60)
    print("MLB Contract Advisor - Database Seeding")
    print("=" * 60)

    # Load master dataset
    data_path = MASTER_DATA_DIR / "Master Data" / "master_contract_dataset.csv"

    # Try alternate path if first doesn't exist
    if not data_path.exists():
        data_path = FANGRAPHS_DATA_DIR / "Master Data" / "master_contract_dataset.csv"

    if not data_path.exists():
        print(f"Error: master_contract_dataset.csv not found")
        print("Run the data integration pipeline first!")
        return

    df = pd.read_csv(data_path)
    print(f"Loaded {len(df)} contracts from master dataset")

    # Load FanGraphs data for recent stats
    batting_path = FANGRAPHS_DATA_DIR / "fangraphs_batting_2015-2025.csv"
    pitching_path = FANGRAPHS_DATA_DIR / "fangraphs_pitching_2015-2025.csv"

    batting_df = None
    pitching_df = None

    if batting_path.exists() and pitching_path.exists():
        batting_df = pd.read_csv(batting_path)
        pitching_df = pd.read_csv(pitching_path)
        # Add normalized names for matching
        batting_df['_normalized_name'] = batting_df['Name'].apply(normalize_name)
        pitching_df['_normalized_name'] = pitching_df['Name'].apply(normalize_name)
        print(f"Loaded FanGraphs data: {len(batting_df)} batting, {len(pitching_df)} pitching seasons")
    else:
        print("Warning: FanGraphs data not found, skipping recent stats")

    # Create tables
    print("\nCreating database tables...")
    Base.metadata.drop_all(bind=engine)  # Clear existing data
    Base.metadata.create_all(bind=engine)
    print("Tables created")

    # Load Statcast data for prospects
    load_statcast_data()

    # Seed data
    db = SessionLocal()
    yearly_stats_count = 0
    try:
        seed_contracts(db, df, batting_df, pitching_df)
        signed_names = seed_signed_players(db, df)
        prospects_count = seed_prospects(db, signed_names)
        yearly_stats_count = seed_yearly_stats(db, batting_df, pitching_df)
        print("\nDatabase seeding complete!")
    finally:
        db.close()

    # Summary
    print("\n" + "=" * 60)
    print("Summary:")
    print(f"  Contracts: {len(df)}")
    print(f"  Signed Players: {df['player_name'].nunique()}")
    print(f"  Prospects: {prospects_count}")
    print(f"  Yearly Stats: {yearly_stats_count}")
    print(f"  Years: {df['year_signed'].min()}-{df['year_signed'].max()}")
    print("=" * 60)


if __name__ == "__main__":
    main()

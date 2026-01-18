"""
Seed the database with contract and player data from the master dataset,
plus prospects from FanGraphs data.
"""
import sys
import os
import re
import unicodedata

# Add app to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pandas as pd
import numpy as np
from pathlib import Path
from app.models.database import engine, Base, Contract, Player, SessionLocal
from app.config import MASTER_DATA_DIR

PITCHER_POSITIONS = ['SP', 'RP', 'P', 'CL']

# Path to FanGraphs data (one level up from backend)
FANGRAPHS_DATA_DIR = Path(__file__).parent.parent / "Data"


def normalize_name(name):
    """
    Normalize player names for matching.
    Handles accents (José→Jose), suffixes (Jr., II), and case.
    """
    if pd.isna(name):
        return ""
    name = str(name)
    # Remove accents
    name = unicodedata.normalize('NFD', name)
    name = ''.join(c for c in name if unicodedata.category(c) != 'Mn')
    # Remove suffixes
    suffixes = [' jr.', ' jr', ' sr.', ' sr', ' ii', ' iii', ' iv', ' v']
    name_lower = name.lower()
    for suffix in suffixes:
        if name_lower.endswith(suffix):
            name = name[:-len(suffix)]
            break
    # Remove special characters and normalize whitespace
    name = re.sub(r"[^\w\s\-]", "", name)
    name = ' '.join(name.split())
    return name.lower().strip()


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


def seed_contracts(db, df):
    """Seed contracts table from master dataset."""
    print(f"Seeding {len(df)} contracts...")

    extensions_count = 0

    for _, row in df.iterrows():
        age = int(row['age_at_signing'])
        length = int(row['length'])
        is_ext = is_likely_extension(age, length)

        if is_ext:
            extensions_count += 1

        contract = Contract(
            player_name=row['player_name'],
            position=row['position'],
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
            is_extension=is_ext,
        )
        db.add(contract)

    db.commit()
    print(f"Seeded {len(df)} contracts ({extensions_count} extensions)")


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
        )
        db.add(player)
        prospects_added += 1

    db.commit()
    print(f"  Seeded {prospects_added} prospects")
    return prospects_added


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

    # Create tables
    print("\nCreating database tables...")
    Base.metadata.drop_all(bind=engine)  # Clear existing data
    Base.metadata.create_all(bind=engine)
    print("Tables created")

    # Seed data
    db = SessionLocal()
    try:
        seed_contracts(db, df)
        signed_names = seed_signed_players(db, df)
        prospects_count = seed_prospects(db, signed_names)
        print("\nDatabase seeding complete!")
    finally:
        db.close()

    # Summary
    print("\n" + "=" * 60)
    print("Summary:")
    print(f"  Contracts: {len(df)}")
    print(f"  Signed Players: {df['player_name'].nunique()}")
    print(f"  Prospects: {prospects_count}")
    print(f"  Years: {df['year_signed'].min()}-{df['year_signed'].max()}")
    print("=" * 60)


if __name__ == "__main__":
    main()

"""
Seed the database with contract and player data from the master dataset.
"""
import sys
import os

# Add app to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pandas as pd
from app.models.database import engine, Base, Contract, Player, SessionLocal
from app.config import MASTER_DATA_DIR

PITCHER_POSITIONS = ['SP', 'RP', 'P', 'CL']


def seed_contracts(db, df):
    """Seed contracts table from master dataset."""
    print(f"Seeding {len(df)} contracts...")

    for _, row in df.iterrows():
        contract = Contract(
            player_name=row['player_name'],
            position=row['position'],
            year_signed=int(row['year_signed']),
            age_at_signing=int(row['age_at_signing']),
            aav=float(row['AAV']),
            total_value=float(row['total_value']) if pd.notna(row.get('total_value')) else None,
            length=int(row['length']),
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
        )
        db.add(contract)

    db.commit()
    print(f"Seeded {len(df)} contracts")


def seed_players(db, df):
    """Seed players table for autocomplete."""
    print("Seeding players...")

    # Get unique players
    unique_players = df.drop_duplicates(subset=['player_name', 'position'])

    for _, row in unique_players.iterrows():
        player = Player(
            name=row['player_name'],
            position=row['position'],
            team=None,  # Could extract from Spotrac if needed
            is_pitcher=row['position'] in PITCHER_POSITIONS
        )
        db.add(player)

    db.commit()
    print(f"Seeded {len(unique_players)} players")


def main():
    """Main seeding function."""
    print("=" * 60)
    print("MLB Contract Advisor - Database Seeding")
    print("=" * 60)

    # Load master dataset
    data_path = MASTER_DATA_DIR / "master_contract_dataset.csv"

    if not data_path.exists():
        print(f"Error: {data_path} not found")
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
        seed_players(db, df)
        print("\nDatabase seeding complete!")
    finally:
        db.close()

    # Summary
    print("\n" + "=" * 60)
    print("Summary:")
    print(f"  Contracts: {len(df)}")
    print(f"  Players: {df['player_name'].nunique()}")
    print(f"  Years: {df['year_signed'].min()}-{df['year_signed'].max()}")
    print("=" * 60)


if __name__ == "__main__":
    main()

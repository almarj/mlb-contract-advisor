"""
Database configuration and models.
"""
from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from app.config import DATABASE_URL

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class Contract(Base):
    """Historical contract data."""
    __tablename__ = "contracts"

    id = Column(Integer, primary_key=True, index=True)
    player_name = Column(String, index=True)
    position = Column(String, index=True)
    signing_team = Column(String, nullable=True, index=True)
    year_signed = Column(Integer, index=True)
    age_at_signing = Column(Integer)
    aav = Column(Float)
    total_value = Column(Float)
    length = Column(Integer)

    # 3-year average stats
    war_3yr = Column(Float)
    wrc_plus_3yr = Column(Float, nullable=True)
    avg_3yr = Column(Float, nullable=True)
    obp_3yr = Column(Float, nullable=True)
    slg_3yr = Column(Float, nullable=True)
    hr_3yr = Column(Float, nullable=True)

    # Pitcher stats
    era_3yr = Column(Float, nullable=True)
    fip_3yr = Column(Float, nullable=True)
    k_9_3yr = Column(Float, nullable=True)
    bb_9_3yr = Column(Float, nullable=True)
    ip_3yr = Column(Float, nullable=True)

    # Statcast
    avg_exit_velo = Column(Float, nullable=True)
    barrel_rate = Column(Float, nullable=True)
    max_exit_velo = Column(Float, nullable=True)
    hard_hit_pct = Column(Float, nullable=True)

    # Plate discipline (percentiles 0-100, batters)
    chase_rate = Column(Float, nullable=True)
    whiff_rate = Column(Float, nullable=True)

    # Pitcher Statcast (percentiles 0-100)
    fb_velocity = Column(Float, nullable=True)  # Fastball velocity percentile
    fb_spin = Column(Float, nullable=True)  # Fastball spin percentile
    xera = Column(Float, nullable=True)  # Expected ERA percentile
    k_percent = Column(Float, nullable=True)  # K% percentile
    bb_percent = Column(Float, nullable=True)  # BB% percentile
    whiff_percent_pitcher = Column(Float, nullable=True)  # Whiff% percentile (pitcher)
    chase_percent_pitcher = Column(Float, nullable=True)  # Chase% induced percentile

    # Contract type flag
    is_extension = Column(Boolean, default=False, index=True)

    # Recent performance stats (last 3 years from current date)
    recent_war_3yr = Column(Float, nullable=True)
    recent_wrc_plus_3yr = Column(Float, nullable=True)
    recent_avg_3yr = Column(Float, nullable=True)
    recent_obp_3yr = Column(Float, nullable=True)
    recent_slg_3yr = Column(Float, nullable=True)
    recent_hr_3yr = Column(Float, nullable=True)
    recent_era_3yr = Column(Float, nullable=True)
    recent_fip_3yr = Column(Float, nullable=True)
    recent_k_9_3yr = Column(Float, nullable=True)
    recent_bb_9_3yr = Column(Float, nullable=True)
    recent_ip_3yr = Column(Float, nullable=True)


class Player(Base):
    """Player lookup table for autocomplete."""
    __tablename__ = "players"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    position = Column(String)
    team = Column(String, nullable=True)
    is_pitcher = Column(Boolean, default=False)

    # Distinguish signed vs unsigned (prospect) players
    has_contract = Column(Boolean, default=False, index=True)
    current_age = Column(Integer, nullable=True)
    last_season = Column(Integer, nullable=True)

    # 3-year average stats (for prospects without Contract records)
    war_3yr = Column(Float, nullable=True)
    wrc_plus_3yr = Column(Float, nullable=True)
    avg_3yr = Column(Float, nullable=True)
    obp_3yr = Column(Float, nullable=True)
    slg_3yr = Column(Float, nullable=True)
    hr_3yr = Column(Float, nullable=True)

    # Pitcher stats
    era_3yr = Column(Float, nullable=True)
    fip_3yr = Column(Float, nullable=True)
    k_9_3yr = Column(Float, nullable=True)
    bb_9_3yr = Column(Float, nullable=True)
    ip_3yr = Column(Float, nullable=True)

    # Batter Statcast
    avg_exit_velo = Column(Float, nullable=True)
    barrel_rate = Column(Float, nullable=True)
    max_exit_velo = Column(Float, nullable=True)
    hard_hit_pct = Column(Float, nullable=True)
    chase_rate = Column(Float, nullable=True)  # Plate discipline percentile
    whiff_rate = Column(Float, nullable=True)  # Plate discipline percentile

    # Pitcher Statcast (percentiles 0-100)
    fb_velocity = Column(Float, nullable=True)
    fb_spin = Column(Float, nullable=True)
    xera = Column(Float, nullable=True)
    k_percent = Column(Float, nullable=True)
    bb_percent = Column(Float, nullable=True)
    whiff_percent_pitcher = Column(Float, nullable=True)
    chase_percent_pitcher = Column(Float, nullable=True)


class PlayerYearlyStats(Base):
    """
    Year-by-year stats for players.
    Pre-computed during seeding for fast lookups when expanding contract rows.
    """
    __tablename__ = "player_yearly_stats"

    id = Column(Integer, primary_key=True, index=True)
    player_name = Column(String, index=True)
    normalized_name = Column(String, index=True)  # For fast lookups
    season = Column(Integer, index=True)
    team = Column(String, nullable=True)
    is_pitcher = Column(Boolean, default=False)

    # Common stats
    games = Column(Integer, nullable=True)
    war = Column(Float, nullable=True)

    # Batter stats
    pa = Column(Integer, nullable=True)
    wrc_plus = Column(Float, nullable=True)
    avg = Column(Float, nullable=True)
    obp = Column(Float, nullable=True)
    slg = Column(Float, nullable=True)
    hr = Column(Integer, nullable=True)
    rbi = Column(Integer, nullable=True)
    runs = Column(Integer, nullable=True)
    hits = Column(Integer, nullable=True)
    sb = Column(Integer, nullable=True)

    # Pitcher stats
    wins = Column(Integer, nullable=True)
    losses = Column(Integer, nullable=True)
    era = Column(Float, nullable=True)
    fip = Column(Float, nullable=True)
    k_9 = Column(Float, nullable=True)
    bb_9 = Column(Float, nullable=True)
    ip = Column(Float, nullable=True)

    # Composite index for common query pattern
    __table_args__ = (
        Index('ix_player_yearly_stats_lookup', 'normalized_name', 'is_pitcher', 'season'),
    )


def get_db():
    """Dependency for database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Create all tables."""
    Base.metadata.create_all(bind=engine)


def run_migrations():
    """
    Run simple schema migrations for new columns.
    SQLAlchemy's create_all doesn't add columns to existing tables,
    so we need to do this manually.
    """
    import logging
    from sqlalchemy import text, inspect

    logger = logging.getLogger(__name__)

    with engine.connect() as conn:
        inspector = inspect(engine)

        # Check if contracts table exists
        if 'contracts' not in inspector.get_table_names():
            logger.info("Contracts table doesn't exist yet, skipping migrations")
            return

        # Get existing columns in contracts table
        existing_columns = [col['name'] for col in inspector.get_columns('contracts')]

        # Migration: Add signing_team column if it doesn't exist
        if 'signing_team' not in existing_columns:
            logger.info("Adding signing_team column to contracts table...")
            conn.execute(text(
                "ALTER TABLE contracts ADD COLUMN signing_team VARCHAR"
            ))
            conn.commit()
            logger.info("signing_team column added successfully")

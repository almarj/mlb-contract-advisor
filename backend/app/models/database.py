"""
Database configuration and models.
"""
from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean
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

    # Contract type flag
    is_extension = Column(Boolean, default=False, index=True)


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

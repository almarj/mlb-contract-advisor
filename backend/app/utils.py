"""
Shared utilities for the MLB Contract Advisor backend.
"""
import unicodedata
import re
import logging
from datetime import datetime
from typing import List

# Configure module logger
logger = logging.getLogger(__name__)

# =============================================================================
# Constants
# =============================================================================

# Pitcher positions for determining player type
PITCHER_POSITIONS = frozenset(['SP', 'RP', 'P', 'CL'])

# Position groupings for similarity matching
POSITION_GROUPS = {
    'SP': 'SP', 'RP': 'RP', 'CL': 'RP', 'P': 'SP',
    'C': 'C', '1B': '1B', '2B': '2B', '3B': '3B', 'SS': 'SS',
    'LF': 'OF', 'CF': 'OF', 'RF': 'OF', 'OF': 'OF', 'DH': 'DH',
}

# Name suffixes to strip during normalization
NAME_SUFFIXES = [' jr.', ' jr', ' sr.', ' sr', ' ii', ' iii', ' iv', ' v']

# MLB season typically ends in early October
SEASON_END_MONTH = 10

# Default values for missing stats (used in prediction feature imputation)
DEFAULT_BATTER_STATS = {
    'wrc_plus': 100,
    'avg': 0.250,
    'obp': 0.320,
    'slg': 0.400,
    'hr': 15,
    'exit_velo': 88.5,
    'barrel_rate': 8.0,
    'max_exit_velo': 110.0,
    'hard_hit_pct': 40.0,
    'chase_rate': 50.0,  # Percentile, 50 = average
    'whiff_rate': 50.0,  # Percentile, 50 = average
}

DEFAULT_PITCHER_STATS = {
    'era': 4.00,
    'fip': 4.00,
    'k_9': 8.0,
    'bb_9': 3.0,
    'ip': 150,
    'fb_velocity': 50.0,  # Percentile
    'fb_spin': 50.0,
    'xera': 50.0,
    'k_percent': 50.0,
    'bb_percent': 50.0,
    'whiff_percent_pitcher': 50.0,
    'chase_percent_pitcher': 50.0,
}

# Confidence score cap (model accuracy rarely exceeds this in practice)
MAX_CONFIDENCE_SCORE = 95


# =============================================================================
# Name normalization
# =============================================================================

def normalize_name(name: str) -> str:
    """
    Normalize a player name for consistent matching.

    Handles:
    - Unicode accents (José → Jose)
    - Name suffixes (Jr., Sr., II, III, etc.)
    - Extra whitespace
    - Special characters

    Args:
        name: The player name to normalize

    Returns:
        Lowercase, accent-free, suffix-free normalized name
    """
    if not name:
        return ""

    # Remove accents via Unicode normalization
    name = unicodedata.normalize('NFD', name)
    name = ''.join(c for c in name if unicodedata.category(c) != 'Mn')

    # Remove common suffixes
    name_lower = name.lower()
    for suffix in NAME_SUFFIXES:
        if name_lower.endswith(suffix):
            name = name[:-len(suffix)]
            break

    # Remove special characters except spaces and hyphens
    name = re.sub(r"[^\w\s\-]", "", name)

    # Normalize whitespace and lowercase
    return ' '.join(name.split()).lower().strip()


# =============================================================================
# Position utilities
# =============================================================================

def is_pitcher(position: str) -> bool:
    """
    Check if a position is a pitcher position.

    Args:
        position: The position string (e.g., 'SP', 'RF', '1B')

    Returns:
        True if the position is a pitcher, False otherwise
    """
    return position.upper() in PITCHER_POSITIONS


def get_position_group(position: str) -> str:
    """
    Get the position group for similarity matching.

    Args:
        position: The position string

    Returns:
        The position group (e.g., 'OF' for outfielders)
    """
    return POSITION_GROUPS.get(position.upper(), 'OF')


# =============================================================================
# Date utilities
# =============================================================================

def get_current_year() -> int:
    """
    Get the current year for features like year_signed.

    Returns:
        The current calendar year
    """
    return datetime.now().year


def get_recent_completed_seasons(num_years: int = 3) -> List[int]:
    """
    Dynamically determine the last N completed MLB seasons.

    MLB season typically ends in early October, so:
    - If current month >= October, current year is complete
    - Otherwise, last complete season is previous year

    Args:
        num_years: Number of recent seasons to return

    Returns:
        List of season years, e.g., [2023, 2024, 2025]
    """
    now = datetime.now()
    current_year = now.year
    current_month = now.month

    # Determine the most recent completed season
    if current_month >= SEASON_END_MONTH:
        last_complete_season = current_year
    else:
        last_complete_season = current_year - 1

    # Return the last N seasons
    return list(range(last_complete_season - num_years + 1, last_complete_season + 1))


# =============================================================================
# Search sanitization
# =============================================================================

def sanitize_search_query(query: str) -> str:
    """
    Sanitize a search query to prevent SQL LIKE pattern abuse.

    Escapes % and _ characters that have special meaning in LIKE patterns.

    Args:
        query: The raw search query

    Returns:
        Sanitized query safe for LIKE patterns
    """
    if not query:
        return ""
    # Escape SQL LIKE special characters
    return query.replace('%', r'\%').replace('_', r'\_')

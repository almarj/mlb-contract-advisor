"""
Context Service - Builds context for Claude from database and predictions.
"""
import logging
import re
from typing import Optional, Tuple, List
from sqlalchemy.orm import Session

from app.models.database import Player, Contract, PlayerYearlyStats
from app.models.schemas import PredictionResponse, ComparablePlayer

logger = logging.getLogger(__name__)


class ContextService:
    """Service for extracting player names and building context for Claude."""

    def extract_player_name(self, query: str, db: Session) -> Tuple[Optional[str], List[str]]:
        """
        Extract a player name from a natural language query.

        Returns:
            Tuple of (matched_player_name, suggestions_if_ambiguous)
        """
        # Clean the query
        query_lower = query.lower().strip()

        # Remove common question patterns to isolate the player name
        patterns_to_remove = [
            # Value/worth questions
            r"what would (.+?) be worth",
            r"what is (.+?) worth",
            r"how much is (.+?) worth",
            r"how much should (.+?) get",
            r"what should (.+?) get",
            # Prediction questions
            r"predict (.+?)('s)? contract",
            r"predict for (.+)",
            # Assessment questions (is contract worth it, overpaid, etc.)
            r"is (.+?)('s)? contract worth",
            r"is (.+?) worth (his|her|their) contract",
            r"is (.+?) overpaid",
            r"is (.+?) underpaid",
            r"did (.+?) deserve",
            r"should (.+?) have (gotten|got|received)",
            r"was (.+?) worth",
            # Stats questions
            r"what is (.+?)('s)? war",
            r"what is (.+?)('s)? era",
            r"what is (.+?)('s)? avg",
            r"what are (.+?)('s)? stats",
            r"how good is (.+)",
            r"how did (.+?) perform",
            # General questions
            r"what about (.+)",
            r"tell me about (.+)",
            r"show me (.+)",
            r"analyze (.+)",
        ]

        extracted_name = None
        for pattern in patterns_to_remove:
            match = re.search(pattern, query_lower)
            if match:
                extracted_name = match.group(1).strip()
                # Remove possessive
                extracted_name = extracted_name.replace("'s", "").strip()
                break

        # If no pattern matched, use the whole query as a potential name
        if not extracted_name:
            # Remove common words
            stop_words = [
                # Question words
                "what", "how", "much", "is", "would", "be", "worth", "are", "was", "did",
                # Contract-related
                "the", "contract", "for", "about", "tell", "me", "show", "predict", "get",
                "should", "can", "you", "his", "her", "their", "overpaid", "underpaid",
                "deserve", "gotten", "got", "received", "analyze", "good", "perform",
                # Prediction-related
                "predicted", "prediction", "value", "salary", "paid", "pay", "money",
                "projected", "projection", "estimate", "estimated", "aav", "annual",
                # Stats-related
                "war", "era", "avg", "stats", "batting", "pitching", "average",
            ]
            words = query_lower.split()
            name_words = [w for w in words if w not in stop_words and len(w) > 1]
            if name_words:
                extracted_name = " ".join(name_words)

        if not extracted_name or len(extracted_name) < 2:
            return None, []

        # Search database for matching players
        players = db.query(Player).filter(
            Player.name.ilike(f"%{extracted_name}%")
        ).order_by(Player.has_contract.desc()).limit(10).all()

        if not players:
            # Try searching for each word individually
            # Prioritize last word first (usually last name, more unique)
            words = extracted_name.split()
            words_to_try = list(reversed(words))  # Try last name first

            for word in words_to_try:
                if len(word) >= 3:
                    candidates = db.query(Player).filter(
                        Player.name.ilike(f"%{word}%")
                    ).order_by(Player.has_contract.desc()).limit(10).all()

                    if candidates:
                        # If we have multiple words, prefer candidates that match more words
                        if len(words) > 1:
                            # Score candidates by how many query words they match
                            scored = []
                            for c in candidates:
                                name_lower = c.name.lower()
                                matches = sum(1 for w in words if w in name_lower)
                                scored.append((matches, c))
                            scored.sort(key=lambda x: x[0], reverse=True)
                            players = [c for _, c in scored]
                        else:
                            players = candidates
                        break

        if not players:
            return None, []

        # If only one match, return it
        if len(players) == 1:
            return players[0].name, []

        # Check for exact match (case-insensitive)
        for p in players:
            if p.name.lower() == extracted_name.lower():
                return p.name, []

        # Multiple matches - return first as best guess, rest as suggestions
        suggestions = [p.name for p in players[1:5]]
        return players[0].name, suggestions

    def build_prediction_context(
        self,
        prediction: PredictionResponse,
        player_name: str,
        position: str
    ) -> str:
        """
        Build a formatted context string for Claude from a prediction response.

        Args:
            prediction: The ML model's prediction response
            player_name: Player name
            position: Player position

        Returns:
            Formatted context string
        """
        # Format AAV in millions
        aav_millions = prediction.predicted_aav / 1_000_000
        aav_low_millions = prediction.predicted_aav_low / 1_000_000
        aav_high_millions = prediction.predicted_aav_high / 1_000_000

        context = f"""Player: {player_name} ({position})

PREDICTION (from our ML model - use these exact numbers):
- Predicted AAV: ${aav_millions:.1f}M per year
- Predicted Length: {prediction.predicted_length} years
- Total Value: ${aav_millions * prediction.predicted_length:.1f}M
- Range: ${aav_low_millions:.1f}M - ${aav_high_millions:.1f}M
- Confidence: {prediction.confidence_score:.0f}%
- Model Accuracy: {prediction.model_accuracy:.0f}% of predictions within $5M of actual"""

        # Add actual contract if player has one (for assessment)
        if prediction.actual_aav:
            actual_aav_millions = prediction.actual_aav / 1_000_000
            context += f"""

ACTUAL CONTRACT (player is signed):
- Actual AAV: ${actual_aav_millions:.1f}M per year
- Actual Length: {prediction.actual_length} years"""

            # Calculate if overpaid/underpaid
            diff = actual_aav_millions - aav_millions
            if abs(diff) < 2:
                assessment = "Fair Value"
            elif diff > 0:
                assessment = f"Overpaid by ${abs(diff):.1f}M/year"
            else:
                assessment = f"Underpaid by ${abs(diff):.1f}M/year"
            context += f"\n- Assessment: {assessment}"

        # Add feature importance
        if prediction.feature_importance:
            context += "\n\nKEY FACTORS (top features driving this prediction):"
            for i, (feature, importance) in enumerate(prediction.feature_importance.items()):
                if i >= 3:
                    break
                # Make feature names more readable
                readable_name = feature.replace("_", " ").replace("3yr", "(3-year avg)")
                context += f"\n- {readable_name}: {importance*100:.1f}% importance"

        # Add comparables
        comparables = prediction.comparables_recent or prediction.comparables
        if comparables:
            context += "\n\nCOMPARABLE PLAYERS (similar recent signings):"
            for comp in comparables[:3]:
                comp_aav_millions = comp.aav / 1_000_000 if comp.aav > 1000 else comp.aav
                ext_note = " (pre-FA extension)" if comp.is_extension else ""
                context += f"\n- {comp.name} ({comp.position}): ${comp_aav_millions:.1f}M/{comp.length}yr in {comp.year_signed}, {comp.war_3yr:.1f} WAR, {comp.similarity_score:.0f}% similar{ext_note}"

        return context

    def build_not_found_context(self, query: str, suggestions: List[str]) -> str:
        """Build context for when a player is not found."""
        context = f"""Player: NOT FOUND
Query: "{query}"
Database: 450+ MLB contracts from 2015-2025

The player could not be identified in our database."""

        if suggestions:
            context += f"\n\nDid you mean one of these players?\n"
            for s in suggestions:
                context += f"- {s}\n"

        return context

    def build_stats_context(self, player_name: str, db: Session) -> str:
        """
        Build context with year-by-year player stats.

        Args:
            player_name: Player name to look up
            db: Database session

        Returns:
            Formatted stats context string
        """
        # Normalize name for lookup
        normalized = player_name.lower().strip()

        # Get recent yearly stats (last 5 years)
        stats = db.query(PlayerYearlyStats).filter(
            PlayerYearlyStats.normalized_name == normalized
        ).order_by(PlayerYearlyStats.season.desc()).limit(5).all()

        if not stats:
            # Try partial match
            stats = db.query(PlayerYearlyStats).filter(
                PlayerYearlyStats.player_name.ilike(f"%{player_name}%")
            ).order_by(PlayerYearlyStats.season.desc()).limit(5).all()

        if not stats:
            return ""

        is_pitcher = stats[0].is_pitcher if stats else False

        context = "\n\nPLAYER STATISTICS (recent seasons):"

        for s in stats:
            context += f"\n\n{s.season} Season ({s.team or 'Unknown'}):"
            context += f"\n- Games: {s.games or 'N/A'}"
            context += f"\n- WAR: {s.war:.1f}" if s.war is not None else ""

            if is_pitcher:
                # Pitcher stats
                if s.wins is not None or s.losses is not None:
                    context += f"\n- Record: {s.wins or 0}-{s.losses or 0}"
                if s.era is not None:
                    context += f"\n- ERA: {s.era:.2f}"
                if s.ip is not None:
                    context += f"\n- IP: {s.ip:.1f}"
                if s.fip is not None:
                    context += f"\n- FIP: {s.fip:.2f}"
                if s.k_9 is not None:
                    context += f"\n- K/9: {s.k_9:.1f}"
                if s.bb_9 is not None:
                    context += f"\n- BB/9: {s.bb_9:.1f}"
            else:
                # Batter stats
                if s.avg is not None:
                    context += f"\n- AVG: {s.avg:.3f}"
                if s.obp is not None:
                    context += f"\n- OBP: {s.obp:.3f}"
                if s.slg is not None:
                    context += f"\n- SLG: {s.slg:.3f}"
                if s.wrc_plus is not None:
                    context += f"\n- wRC+: {int(s.wrc_plus)}"
                if s.hr is not None:
                    context += f"\n- HR: {s.hr}"
                if s.rbi is not None:
                    context += f"\n- RBI: {s.rbi}"
                if s.sb is not None:
                    context += f"\n- SB: {s.sb}"

        return context

    def is_two_way_player(self, player_name: str, db: Session) -> bool:
        """
        Check if a player has both batting and pitching records.

        Args:
            player_name: Player name to check
            db: Database session

        Returns:
            True if player has records as both batter and pitcher
        """
        # Check for both batter and pitcher yearly stats
        batter_stats = db.query(PlayerYearlyStats).filter(
            PlayerYearlyStats.player_name.ilike(f"%{player_name}%"),
            PlayerYearlyStats.is_pitcher == False
        ).first()

        pitcher_stats = db.query(PlayerYearlyStats).filter(
            PlayerYearlyStats.player_name.ilike(f"%{player_name}%"),
            PlayerYearlyStats.is_pitcher == True
        ).first()

        return batter_stats is not None and pitcher_stats is not None

    def get_two_way_stats(self, player_name: str, db: Session) -> dict:
        """
        Get separate batting and pitching stats for a two-way player.

        Args:
            player_name: Player name
            db: Database session

        Returns:
            Dict with 'batting' and 'pitching' stats averages
        """
        result = {'batting': None, 'pitching': None}

        # Get batting stats (3-year avg)
        batter_stats = db.query(PlayerYearlyStats).filter(
            PlayerYearlyStats.player_name.ilike(f"%{player_name}%"),
            PlayerYearlyStats.is_pitcher == False
        ).order_by(PlayerYearlyStats.season.desc()).limit(3).all()

        if batter_stats:
            wars = [s.war for s in batter_stats if s.war is not None]
            wrcs = [s.wrc_plus for s in batter_stats if s.wrc_plus is not None]
            result['batting'] = {
                'war_3yr': sum(wars) / len(wars) if wars else None,
                'wrc_plus_3yr': sum(wrcs) / len(wrcs) if wrcs else None,
                'seasons': len(batter_stats)
            }

        # Get pitching stats (3-year avg)
        pitcher_stats = db.query(PlayerYearlyStats).filter(
            PlayerYearlyStats.player_name.ilike(f"%{player_name}%"),
            PlayerYearlyStats.is_pitcher == True
        ).order_by(PlayerYearlyStats.season.desc()).limit(3).all()

        if pitcher_stats:
            wars = [s.war for s in pitcher_stats if s.war is not None]
            eras = [s.era for s in pitcher_stats if s.era is not None]
            ips = [s.ip for s in pitcher_stats if s.ip is not None]
            result['pitching'] = {
                'war_3yr': sum(wars) / len(wars) if wars else None,
                'era_3yr': sum(eras) / len(eras) if eras else None,
                'ip_3yr': sum(ips) / len(ips) if ips else None,
                'seasons': len(pitcher_stats)
            }

        return result

    def build_two_way_context(
        self,
        player_name: str,
        batter_prediction: dict,
        pitcher_prediction: dict,
        actual_aav: float = None,
        actual_length: int = None
    ) -> str:
        """
        Build context for a two-way player showing both predictions.

        Args:
            player_name: Player name
            batter_prediction: Prediction result for batting role
            pitcher_prediction: Prediction result for pitching role
            actual_aav: Actual contract AAV (if signed)
            actual_length: Actual contract length (if signed)

        Returns:
            Formatted context string
        """
        # Calculate combined prediction
        batter_aav = batter_prediction.get('predicted_aav', 0)
        pitcher_aav = pitcher_prediction.get('predicted_aav', 0)
        combined_aav = batter_aav + pitcher_aav

        context = f"""Player: {player_name} (TWO-WAY PLAYER - DH + SP)

⚾ TWO-WAY PLAYER ANALYSIS (UNIQUE CASE):
This player contributes as BOTH a hitter AND a pitcher. We evaluate each role separately.

BATTING VALUE (as DH):
- Predicted AAV: ${batter_aav:.1f}M per year
- Predicted Length: {batter_prediction.get('predicted_length', 'N/A')} years
- Confidence: {batter_prediction.get('confidence_score', 0):.0f}%

PITCHING VALUE (as SP):
- Predicted AAV: ${pitcher_aav:.1f}M per year
- Predicted Length: {pitcher_prediction.get('predicted_length', 'N/A')} years
- Confidence: {pitcher_prediction.get('confidence_score', 0):.0f}%

COMBINED TWO-WAY VALUE:
- Total Predicted AAV: ${combined_aav:.1f}M per year
- This represents the value of getting BOTH an elite hitter AND elite pitcher in one roster spot"""

        if actual_aav:
            actual_aav_millions = actual_aav / 1_000_000
            context += f"""

ACTUAL CONTRACT:
- Actual AAV: ${actual_aav_millions:.1f}M per year
- Actual Length: {actual_length} years"""

            diff = actual_aav_millions - combined_aav
            if abs(diff) < 5:
                assessment = "Fair Value (within model range)"
            elif diff > 0:
                assessment = f"Premium of ${abs(diff):.1f}M/year (accounts for uniqueness/marketability)"
            else:
                assessment = f"Discount of ${abs(diff):.1f}M/year"
            context += f"\n- Assessment: {assessment}"

        context += """

NOTE: Traditional models struggle with two-way players because there's no historical precedent.
The combined value represents what teams would pay for two separate players with these skills."""

        return context


# Singleton instance
context_service = ContextService()

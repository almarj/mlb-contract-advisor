"""
Claude AI Service - Explains ML model predictions using Anthropic's Claude API.
"""
import logging
import asyncio
from typing import Dict, Optional

from app.config import ANTHROPIC_API_KEY, CLAUDE_MODEL, CLAUDE_TIMEOUT

logger = logging.getLogger(__name__)

# System prompt that enforces "explainer only" behavior
SYSTEM_PROMPT = """You are an MLB contract and stats expert. Your primary job is to explain predictions from our ML model, but you can also answer questions about player statistics when data is provided.

CRITICAL RULES FOR PREDICTIONS:
❌ NEVER generate your own AAV or contract length predictions
❌ NEVER estimate a player's value independently
❌ NEVER adjust or round numbers differently than provided
❌ NEVER create comparables not in the provided list
✅ ALWAYS use exact numbers from the model output
✅ ALWAYS cite the model as the source of truth

WHAT YOU CAN DO:
1. Explain contract predictions (exact numbers as provided)
2. Explain what features drove the prediction
3. Discuss similar players and why they're comparable
4. Answer questions about player stats when PLAYER STATISTICS section is provided
5. Provide context about a player's performance and value

STATS QUESTIONS:
- When asked about WAR, ERA, batting average, etc., use the PLAYER STATISTICS section if available
- Cite specific seasons and numbers from the data
- Compare stats across seasons to show trends

IF PLAYER NOT FOUND:
Say: "We don't have data for this player in our database yet. Our database includes 450+ MLB contracts from 2015-2025."

FORMAT:
- Keep responses to 2-3 paragraphs (150-250 words)
- Use exact AAV format provided (e.g., "$12.3M")
- Be conversational but data-driven
- End with suggested actions using this format:
  [ACTION:view_prediction:PlayerName] - to see full prediction details
  [ACTION:compare_players:Player1,Player2] - to compare two players
  [ACTION:show_contracts:position=OF] - to browse contracts

TONE:
- Professional but accessible
- Acknowledge uncertainty when confidence is below 70%
- Be helpful and suggest next steps"""

# Fallback template when Claude is unavailable
FALLBACK_TEMPLATE = """Based on our ML model's analysis, {player_name} ({position}) is projected to receive a contract worth **${predicted_aav:.1f}M per year** over **{predicted_length} years**.

This prediction is based on their recent performance metrics, with a model confidence of {confidence_score:.0f}%. The key factors driving this prediction are their WAR and other statistical indicators.

For a detailed breakdown including comparable players and feature importance, click "View Full Prediction" below.

[ACTION:view_prediction:{player_name}]"""

# Fallback template when player not found
NOT_FOUND_TEMPLATE = """We couldn't find "{query}" in our database of MLB contracts.

Our database includes 450+ MLB contracts from 2015-2025. Try searching for a different player name, or browse our contracts database to explore available players.

[ACTION:show_contracts:]"""


class ClaudeService:
    """Service for generating explanations using Claude API."""

    def __init__(self):
        self._client = None
        self._available = False
        self._init_client()

    def _init_client(self):
        """Initialize the Anthropic client if API key is available."""
        if not ANTHROPIC_API_KEY:
            logger.warning("ANTHROPIC_API_KEY not set - Claude service will use fallback mode")
            return

        try:
            import anthropic
            self._client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
            self._available = True
            logger.info("Claude service initialized successfully")
        except ImportError:
            logger.error("anthropic package not installed")
        except Exception as e:
            logger.error(f"Failed to initialize Claude client: {e}")

    @property
    def is_available(self) -> bool:
        """Check if Claude API is available."""
        return self._available and self._client is not None

    async def generate_explanation(
        self,
        query: str,
        context: str,
        timeout: Optional[int] = None
    ) -> Dict:
        """
        Generate an explanation for a prediction using Claude.

        Args:
            query: User's natural language query
            context: Formatted context with prediction data
            timeout: Optional timeout in seconds (default: CLAUDE_TIMEOUT)

        Returns:
            Dict with:
                - explanation: str - Claude's response or fallback
                - actions: list - Parsed action suggestions
                - success: bool - Whether Claude responded
                - used_fallback: bool - Whether fallback was used
        """
        timeout = timeout or CLAUDE_TIMEOUT

        if not self.is_available:
            logger.info("Claude not available, using fallback")
            return self._create_fallback_response(context)

        try:
            # Run Claude API call with timeout
            response = await asyncio.wait_for(
                self._call_claude(query, context),
                timeout=timeout
            )
            return {
                "explanation": response,
                "actions": self._parse_actions(response),
                "success": True,
                "used_fallback": False
            }
        except asyncio.TimeoutError:
            logger.warning(f"Claude API timeout after {timeout}s")
            return self._create_fallback_response(context, error="timeout")
        except Exception as e:
            logger.error(f"Claude API error: {e}")
            return self._create_fallback_response(context, error=str(e))

    async def _call_claude(self, query: str, context: str) -> str:
        """Make the actual Claude API call."""
        # Build the user message with context
        user_message = f"""User Question: {query}

--- PREDICTION DATA (Use exact numbers from here) ---
{context}
--- END PREDICTION DATA ---

Please explain this prediction to the user in a helpful, conversational way. Remember to use the exact numbers provided and suggest relevant actions."""

        # Run synchronous API call in thread pool
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: self._client.messages.create(
                model=CLAUDE_MODEL,
                max_tokens=500,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_message}]
            )
        )

        return response.content[0].text

    def _create_fallback_response(
        self,
        context: str,
        error: Optional[str] = None
    ) -> Dict:
        """Create a fallback response when Claude is unavailable."""
        # Check if this is a "not found" context
        if "Player: NOT FOUND" in context:
            # Extract query from context
            query = "this player"
            for line in context.split('\n'):
                if "Query:" in line:
                    query = line.split('"')[1] if '"' in line else "this player"
                    break

            explanation = NOT_FOUND_TEMPLATE.format(query=query)
            return {
                "explanation": explanation,
                "actions": self._parse_actions(explanation),
                "success": False,
                "used_fallback": True,
                "error": error
            }

        # Try to extract data from context for template
        try:
            # Parse basic info from context (simple extraction)
            lines = context.split('\n')
            player_name = "this player"
            position = ""
            predicted_aav = 0.0
            predicted_length = 1
            confidence_score = 70.0

            for line in lines:
                if "Player:" in line:
                    parts = line.replace("Player:", "").strip()
                    if "(" in parts:
                        player_name = parts.split("(")[0].strip()
                        position = parts.split("(")[1].replace(")", "").strip()
                elif "Predicted AAV:" in line:
                    # Extract number from "$X.XM" format
                    aav_str = line.split("$")[1].split("M")[0] if "$" in line else "10"
                    predicted_aav = float(aav_str.replace(",", ""))
                elif "Length:" in line:
                    length_str = line.split(":")[1].strip().split()[0]
                    predicted_length = int(float(length_str))
                elif "Confidence:" in line:
                    conf_str = line.split(":")[1].strip().replace("%", "")
                    confidence_score = float(conf_str)

            explanation = FALLBACK_TEMPLATE.format(
                player_name=player_name,
                position=position,
                predicted_aav=predicted_aav,
                predicted_length=predicted_length,
                confidence_score=confidence_score
            )
        except Exception as e:
            logger.warning(f"Failed to parse context for fallback: {e}")
            explanation = "We encountered an issue generating a detailed explanation. Please view the full prediction for complete details.\n\n[ACTION:view_prediction:unknown]"

        return {
            "explanation": explanation,
            "actions": self._parse_actions(explanation),
            "success": False,
            "used_fallback": True,
            "error": error
        }

    def _parse_actions(self, text: str) -> list:
        """Parse action markers from Claude's response."""
        import re
        actions = []

        # Pattern: [ACTION:type:params]
        pattern = r'\[ACTION:(\w+):([^\]]+)\]'
        matches = re.findall(pattern, text)

        for action_type, params in matches:
            action = {
                "action_type": action_type,
                "target_player": None,
                "parameters": {}
            }

            # Parse based on action type
            if action_type == "view_prediction":
                action["target_player"] = params.strip()
            elif action_type == "compare_players":
                players = [p.strip() for p in params.split(",")]
                if len(players) >= 2:
                    action["parameters"] = {
                        "player1": players[0],
                        "player2": players[1]
                    }
            elif action_type == "show_contracts":
                # Parse key=value pairs
                for pair in params.split(","):
                    if "=" in pair:
                        key, value = pair.split("=", 1)
                        action["parameters"][key.strip()] = value.strip()

            actions.append(action)

        return actions


# Singleton instance
claude_service = ClaudeService()

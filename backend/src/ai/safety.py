"""
AI Safety Filter and Guardrails.

Provides content moderation and safety checks for AI-generated messages:
1. Banned phrase detection
2. Profanity filtering
3. Tone analysis (appropriate vs inappropriate)
4. OpenAI Moderation API integration
5. Fallback templates for rejected content
"""
import re
from typing import Optional, Dict, List, Tuple
from enum import Enum

from src.lib.logging import get_logger
from src.ai.client import get_openai_client

logger = get_logger(__name__)


class SafetyCheckResult(str, Enum):
    """Safety check result status."""
    PASSED = "passed"
    FAILED = "failed"
    WARNING = "warning"


class ToneCategory(str, Enum):
    """Message tone categories."""
    PROFESSIONAL = "professional"
    FRIENDLY = "friendly"
    CASUAL = "casual"
    URGENT = "urgent"
    INAPPROPRIATE = "inappropriate"
    AGGRESSIVE = "aggressive"


# Banned phrases (expandable based on business rules)
BANNED_PHRASES = [
    # Profanity (Bengali)
    r'\b(মাগি|মাগির|খানকি|বেশ্যা|হারামি|হারামজাদা)\b',
    
    # Profanity (English)
    r'\b(fuck|shit|damn|bitch|bastard|asshole|dick|pussy|cock)\b',
    
    # Offensive terms
    r'\b(idiot|stupid|dumb|moron|loser)\b',
    
    # Scam/fraud terms
    r'\b(free\s+money|guaranteed\s+profit|click\s+here\s+now|limited\s+time\s+offer)\b',
    
    # Inappropriate pressure (carefully avoid matching "thank you")
    r'\byou\s+must\b',
    r'\byou\s+should\b(?!\s+know)',  # But allow "you should know"
    r'\byou\s+need\s+to\s+immediately\b',
]

# Inappropriate tone indicators
INAPPROPRIATE_INDICATORS = [
    r'!!!+',  # Three or more exclamation marks
    r'\bURGENT\b.*\bURGENT\b',  # Repeated URGENT
    r'[A-Z]{8,}',  # All caps words (8+ chars to avoid acronyms)
    r'click\s+now',  # Clickbait
    r'act\s+fast',  # High pressure
    r'act\s+immediately',  # High pressure
]

# Professional tone indicators
PROFESSIONAL_INDICATORS = [
    r'\b(please|kindly|thank\s+you|appreciate)\b',
    r'\b(reminder|notice|notification|update)\b',
    r'\b(service|booking|appointment|schedule)\b',
]

# Fallback templates for rejected content
FALLBACK_TEMPLATES = {
    "reminder": {
        "bn": "আপনার সার্ভিস বুকিংয়ের রিমাইন্ডার। বিস্তারিত জানতে অ্যাপে দেখুন।",
        "en": "Reminder about your service booking. Check the app for details.",
    },
    "coaching": {
        "bn": "আপনার জন্য একটি নতুন টিপস এসেছে। অ্যাপে দেখুন।",
        "en": "New coaching tips available. Check the app.",
    },
    "general": {
        "bn": "আপনার জন্য একটি নতুন বার্তা এসেছে।",
        "en": "You have a new message.",
    },
}


class SafetyFilter:
    """
    Safety filter for AI-generated content.
    
    Provides multiple layers of safety checks:
    - Banned phrase detection
    - Tone analysis
    - OpenAI Moderation API (optional)
    """
    
    def __init__(self, use_openai_moderation: bool = False):
        """
        Initialize safety filter.
        
        Args:
            use_openai_moderation: Whether to use OpenAI Moderation API
        """
        self.use_openai_moderation = use_openai_moderation
        self.openai_client = get_openai_client()
        
        # Compile regex patterns for performance
        # Note: Don't use IGNORECASE for inappropriate_patterns as some check for ALL CAPS
        self.banned_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in BANNED_PHRASES]
        self.inappropriate_patterns = [re.compile(pattern) for pattern in INAPPROPRIATE_INDICATORS]  # No IGNORECASE
        self.professional_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in PROFESSIONAL_INDICATORS]
        
        logger.info(f"SafetyFilter initialized (OpenAI moderation: {use_openai_moderation})")
    
    def check_banned_phrases(self, text: str) -> Tuple[SafetyCheckResult, List[str]]:
        """
        Check for banned phrases in text.
        
        Args:
            text: Text to check
            
        Returns:
            Tuple of (result, list of matched phrases)
        """
        matches = []
        
        for pattern in self.banned_patterns:
            found = pattern.findall(text)
            if found:
                matches.extend(found)
        
        if matches:
            logger.warning(f"Banned phrases detected: {matches}")
            return SafetyCheckResult.FAILED, matches
        
        return SafetyCheckResult.PASSED, []
    
    def analyze_tone(self, text: str) -> Tuple[ToneCategory, float]:
        """
        Analyze message tone.
        
        Args:
            text: Text to analyze
            
        Returns:
            Tuple of (tone category, confidence score 0-1)
        """
        # Count inappropriate indicators
        inappropriate_count = sum(
            len(pattern.findall(text))
            for pattern in self.inappropriate_patterns
        )
        
        # Count professional indicators
        professional_count = sum(
            len(pattern.findall(text))
            for pattern in self.professional_patterns
        )
        
        # Determine tone - inappropriate takes priority only if clearly dominant
        if inappropriate_count >= 2:
            confidence = min(inappropriate_count * 0.4, 1.0)
            return ToneCategory.AGGRESSIVE, confidence
        
        if inappropriate_count == 1 and professional_count == 0:
            return ToneCategory.INAPPROPRIATE, 0.6
        
        # Professional wins if we have clear indicators
        if professional_count >= 2:
            return ToneCategory.PROFESSIONAL, min(professional_count * 0.25, 0.9)
        
        if professional_count == 1:
            return ToneCategory.FRIENDLY, 0.7
        
        # Default to casual
        return ToneCategory.CASUAL, 0.5
    
    async def check_openai_moderation(self, text: str) -> Tuple[SafetyCheckResult, Dict]:
        """
        Check content using OpenAI Moderation API.
        
        Args:
            text: Text to check
            
        Returns:
            Tuple of (result, moderation details)
        """
        if not self.use_openai_moderation or not self.openai_client.is_available():
            return SafetyCheckResult.PASSED, {"skipped": True}
        
        try:
            client = self.openai_client.get_client()
            response = client.moderations.create(input=text)
            
            result = response.results[0]
            
            # Check if flagged
            if result.flagged:
                categories = {
                    cat: score
                    for cat, score in result.category_scores.model_dump().items()
                    if score > 0.5  # Only include high-confidence flags
                }
                logger.warning(f"OpenAI moderation flagged content: {categories}")
                return SafetyCheckResult.FAILED, {
                    "flagged": True,
                    "categories": categories,
                }
            
            return SafetyCheckResult.PASSED, {
                "flagged": False,
                "checked": True,
            }
        
        except Exception as e:
            logger.error(f"OpenAI moderation check failed: {e}", exc_info=True)
            return SafetyCheckResult.WARNING, {"error": str(e)}
    
    async def check_message(
        self,
        text: str,
        min_length: int = 10,
        max_length: int = 1000,
    ) -> Dict:
        """
        Perform comprehensive safety check on message.
        
        Args:
            text: Message text to check
            min_length: Minimum allowed length
            max_length: Maximum allowed length
            
        Returns:
            Dictionary with check results:
            {
                "safe": bool,
                "checks": {
                    "length": {...},
                    "banned_phrases": {...},
                    "tone": {...},
                    "openai_moderation": {...}
                },
                "reason": str (if not safe)
            }
        """
        checks = {}
        
        # 1. Length check
        text_length = len(text.strip())
        if text_length < min_length:
            checks["length"] = {
                "status": SafetyCheckResult.FAILED.value,
                "reason": f"Text too short: {text_length} < {min_length}",
            }
            return {
                "safe": False,
                "checks": checks,
                "reason": "Message too short",
            }
        
        if text_length > max_length:
            checks["length"] = {
                "status": SafetyCheckResult.FAILED.value,
                "reason": f"Text too long: {text_length} > {max_length}",
            }
            return {
                "safe": False,
                "checks": checks,
                "reason": "Message too long",
            }
        
        checks["length"] = {
            "status": SafetyCheckResult.PASSED.value,
            "length": text_length,
        }
        
        # 2. Banned phrases check
        banned_result, banned_matches = self.check_banned_phrases(text)
        checks["banned_phrases"] = {
            "status": banned_result.value,
            "matches": banned_matches if banned_matches else None,
        }
        
        if banned_result == SafetyCheckResult.FAILED:
            return {
                "safe": False,
                "checks": checks,
                "reason": f"Contains banned phrases: {', '.join(banned_matches)}",
            }
        
        # 3. Tone analysis
        tone, confidence = self.analyze_tone(text)
        checks["tone"] = {
            "status": SafetyCheckResult.PASSED.value if tone not in [ToneCategory.INAPPROPRIATE, ToneCategory.AGGRESSIVE] else SafetyCheckResult.FAILED.value,
            "category": tone.value,
            "confidence": confidence,
        }
        
        if tone in [ToneCategory.INAPPROPRIATE, ToneCategory.AGGRESSIVE]:
            return {
                "safe": False,
                "checks": checks,
                "reason": f"Inappropriate tone: {tone.value}",
            }
        
        # 4. OpenAI Moderation (optional)
        if self.use_openai_moderation:
            moderation_result, moderation_details = await self.check_openai_moderation(text)
            checks["openai_moderation"] = {
                "status": moderation_result.value,
                "details": moderation_details,
            }
            
            if moderation_result == SafetyCheckResult.FAILED:
                return {
                    "safe": False,
                    "checks": checks,
                    "reason": "Failed OpenAI content moderation",
                }
        
        # All checks passed
        logger.info(f"Safety checks passed for message (length: {text_length}, tone: {tone.value})")
        return {
            "safe": True,
            "checks": checks,
        }
    
    def get_fallback_message(
        self,
        message_type: str = "general",
        locale: str = "bn",
    ) -> str:
        """
        Get fallback message template when content is rejected.
        
        Args:
            message_type: Type of message (reminder, coaching, general)
            locale: Language code (bn, en)
            
        Returns:
            Fallback message text
        """
        # Normalize message type
        msg_type = message_type.lower()
        if msg_type not in FALLBACK_TEMPLATES:
            msg_type = "general"
        
        # Get template for locale
        template = FALLBACK_TEMPLATES[msg_type].get(locale, FALLBACK_TEMPLATES[msg_type]["en"])
        
        logger.info(f"Using fallback template: {msg_type}/{locale}")
        return template


# Global safety filter instance
_safety_filter: Optional[SafetyFilter] = None


def get_safety_filter(use_openai_moderation: bool = False) -> SafetyFilter:
    """
    Get or create global safety filter instance.
    
    Args:
        use_openai_moderation: Whether to use OpenAI Moderation API
        
    Returns:
        SafetyFilter instance
    """
    global _safety_filter
    
    if _safety_filter is None:
        _safety_filter = SafetyFilter(use_openai_moderation=use_openai_moderation)
    
    return _safety_filter


async def check_message_safety(
    text: str,
    use_openai_moderation: bool = False,
    **kwargs
) -> Dict:
    """
    Convenience function to check message safety.
    
    Args:
        text: Message text to check
        use_openai_moderation: Whether to use OpenAI Moderation API
        **kwargs: Additional arguments for check_message()
        
    Returns:
        Safety check results dictionary
    """
    filter_instance = get_safety_filter(use_openai_moderation=use_openai_moderation)
    return await filter_instance.check_message(text, **kwargs)

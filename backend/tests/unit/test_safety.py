"""
Unit tests for AI safety filter and guardrails.
"""
import pytest

from src.ai.safety import (
    SafetyFilter,
    SafetyCheckResult,
    ToneCategory,
    get_safety_filter,
    check_message_safety,
    FALLBACK_TEMPLATES,
)


@pytest.mark.unit
def test_safety_filter_initialization():
    """Test safety filter initialization."""
    filter_instance = SafetyFilter(use_openai_moderation=False)
    assert filter_instance is not None
    assert filter_instance.use_openai_moderation is False


@pytest.mark.unit
def test_check_banned_phrases_clean():
    """Test banned phrase check with clean text."""
    filter_instance = SafetyFilter()
    
    text = "Your booking reminder for tomorrow at 10 AM."
    result, matches = filter_instance.check_banned_phrases(text)
    
    assert result == SafetyCheckResult.PASSED
    assert len(matches) == 0


@pytest.mark.unit
def test_check_banned_phrases_profanity():
    """Test banned phrase check with profanity."""
    filter_instance = SafetyFilter()
    
    text = "This is a fuck test message."
    result, matches = filter_instance.check_banned_phrases(text)
    
    assert result == SafetyCheckResult.FAILED
    assert len(matches) > 0


@pytest.mark.unit
def test_check_banned_phrases_offensive():
    """Test banned phrase check with offensive terms."""
    filter_instance = SafetyFilter()
    
    text = "You are an idiot for missing the booking."
    result, matches = filter_instance.check_banned_phrases(text)
    
    assert result == SafetyCheckResult.FAILED
    assert len(matches) > 0


@pytest.mark.unit
def test_analyze_tone_professional():
    """Test tone analysis for professional message."""
    filter_instance = SafetyFilter()
    
    text = "Please remember your appointment tomorrow. Thank you for using our service."
    tone, confidence = filter_instance.analyze_tone(text)
    
    assert tone == ToneCategory.PROFESSIONAL
    assert confidence > 0.5


@pytest.mark.unit
def test_analyze_tone_friendly():
    """Test tone analysis for friendly message."""
    filter_instance = SafetyFilter()
    
    text = "Your booking is confirmed. Please check the app for details."
    tone, confidence = filter_instance.analyze_tone(text)
    
    assert tone in [ToneCategory.FRIENDLY, ToneCategory.PROFESSIONAL]


@pytest.mark.unit
def test_analyze_tone_inappropriate():
    """Test tone analysis for inappropriate message."""
    filter_instance = SafetyFilter()
    
    text = "URGENT!!! CLICK NOW!!! LIMITED TIME!!!"
    tone, confidence = filter_instance.analyze_tone(text)
    
    assert tone in [ToneCategory.INAPPROPRIATE, ToneCategory.AGGRESSIVE]


@pytest.mark.unit
def test_analyze_tone_casual():
    """Test tone analysis for casual message."""
    filter_instance = SafetyFilter()
    
    text = "Your booking is ready."
    tone, confidence = filter_instance.analyze_tone(text)
    
    # "booking" is a professional keyword, so FRIENDLY or CASUAL is acceptable
    assert tone in [ToneCategory.CASUAL, ToneCategory.FRIENDLY]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_check_message_safe():
    """Test comprehensive message check with safe content."""
    filter_instance = SafetyFilter()
    
    text = "Your service booking is confirmed for tomorrow at 10 AM. Thank you!"
    result = await filter_instance.check_message(text)
    
    assert result["safe"] is True
    assert "checks" in result
    assert result["checks"]["length"]["status"] == SafetyCheckResult.PASSED.value
    assert result["checks"]["banned_phrases"]["status"] == SafetyCheckResult.PASSED.value
    assert result["checks"]["tone"]["status"] == SafetyCheckResult.PASSED.value


@pytest.mark.unit
@pytest.mark.asyncio
async def test_check_message_too_short():
    """Test message check with text too short."""
    filter_instance = SafetyFilter()
    
    text = "Hi"
    result = await filter_instance.check_message(text, min_length=10)
    
    assert result["safe"] is False
    assert "reason" in result
    assert "too short" in result["reason"].lower()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_check_message_too_long():
    """Test message check with text too long."""
    filter_instance = SafetyFilter()
    
    text = "A" * 1001  # 1001 characters
    result = await filter_instance.check_message(text, max_length=1000)
    
    assert result["safe"] is False
    assert "reason" in result
    assert "too long" in result["reason"].lower()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_check_message_with_profanity():
    """Test message check with profanity."""
    filter_instance = SafetyFilter()
    
    text = "Your damn booking is ready."
    result = await filter_instance.check_message(text)
    
    assert result["safe"] is False
    assert "reason" in result
    assert "banned phrase" in result["reason"].lower()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_check_message_inappropriate_tone():
    """Test message check with inappropriate tone."""
    filter_instance = SafetyFilter()
    
    text = "URGENT URGENT!!! ACT NOW OR LOSE YOUR BOOKING!!!"
    result = await filter_instance.check_message(text)
    
    assert result["safe"] is False
    assert "reason" in result
    assert "tone" in result["reason"].lower()


@pytest.mark.unit
def test_get_fallback_message_reminder_bengali():
    """Test getting fallback message for reminder in Bengali."""
    filter_instance = SafetyFilter()
    
    message = filter_instance.get_fallback_message(
        message_type="reminder",
        locale="bn"
    )
    
    assert message is not None
    assert len(message) > 0
    assert message == FALLBACK_TEMPLATES["reminder"]["bn"]


@pytest.mark.unit
def test_get_fallback_message_coaching_english():
    """Test getting fallback message for coaching in English."""
    filter_instance = SafetyFilter()
    
    message = filter_instance.get_fallback_message(
        message_type="coaching",
        locale="en"
    )
    
    assert message is not None
    assert len(message) > 0
    assert message == FALLBACK_TEMPLATES["coaching"]["en"]


@pytest.mark.unit
def test_get_fallback_message_unknown_type():
    """Test getting fallback message for unknown type defaults to general."""
    filter_instance = SafetyFilter()
    
    message = filter_instance.get_fallback_message(
        message_type="unknown_type",
        locale="en"
    )
    
    assert message is not None
    assert message == FALLBACK_TEMPLATES["general"]["en"]


@pytest.mark.unit
def test_get_fallback_message_unknown_locale():
    """Test getting fallback message for unknown locale defaults to English."""
    filter_instance = SafetyFilter()
    
    message = filter_instance.get_fallback_message(
        message_type="reminder",
        locale="fr"  # Not supported
    )
    
    assert message is not None
    assert message == FALLBACK_TEMPLATES["reminder"]["en"]


@pytest.mark.unit
def test_get_safety_filter_singleton():
    """Test that get_safety_filter returns same instance."""
    filter1 = get_safety_filter()
    filter2 = get_safety_filter()
    
    assert filter1 is filter2


@pytest.mark.unit
@pytest.mark.asyncio
async def test_check_message_safety_convenience():
    """Test convenience function for message safety check."""
    text = "Your booking is confirmed. Thank you for using our service."
    result = await check_message_safety(text)
    
    assert result["safe"] is True
    assert "checks" in result


@pytest.mark.unit
@pytest.mark.asyncio
async def test_check_message_safety_unsafe():
    """Test convenience function with unsafe content."""
    text = "You stupid idiot!"
    result = await check_message_safety(text)
    
    assert result["safe"] is False
    assert "reason" in result


@pytest.mark.unit
def test_fallback_templates_structure():
    """Test that fallback templates have proper structure."""
    assert "reminder" in FALLBACK_TEMPLATES
    assert "coaching" in FALLBACK_TEMPLATES
    assert "general" in FALLBACK_TEMPLATES
    
    for msg_type, templates in FALLBACK_TEMPLATES.items():
        assert "bn" in templates
        assert "en" in templates
        assert len(templates["bn"]) > 0
        assert len(templates["en"]) > 0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_check_message_bengali_text():
    """Test message check with Bengali text."""
    filter_instance = SafetyFilter()
    
    text = "আপনার সার্ভিস বুকিং নিশ্চিত করা হয়েছে। ধন্যবাদ।"
    result = await filter_instance.check_message(text)
    
    # Should pass if no banned Bengali phrases
    assert result["safe"] is True


@pytest.mark.unit
@pytest.mark.asyncio
async def test_check_message_mixed_language():
    """Test message check with mixed language."""
    filter_instance = SafetyFilter()
    
    text = "Your booking আগামীকাল confirmed. Thank you ধন্যবাদ।"
    result = await filter_instance.check_message(text)
    
    assert result["safe"] is True


@pytest.mark.unit
def test_tone_analysis_with_emojis():
    """Test tone analysis with emojis."""
    filter_instance = SafetyFilter()
    
    text = "Your booking is ready! 😊 Thank you for choosing us! 🎉"
    tone, confidence = filter_instance.analyze_tone(text)
    
    # Should still detect professional/friendly tone
    assert tone in [ToneCategory.PROFESSIONAL, ToneCategory.FRIENDLY]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_check_message_with_numbers_and_special_chars():
    """Test message check with numbers and special characters."""
    filter_instance = SafetyFilter()
    
    text = "Your booking #12345 is confirmed for 10:30 AM on 2025-11-04. Cost: $50.00."
    result = await filter_instance.check_message(text)
    
    assert result["safe"] is True

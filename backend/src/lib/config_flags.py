"""
Configuration flags and feature toggles for ShoktiAI.

Provides centralized configuration for:
- Frequency caps (outreach limits per customer/worker)
- Feature flags (enable/disable features)
- Campaign presets (default, aggressive, gentle)
- Safety thresholds
"""
from typing import Optional
from pydantic import BaseModel, Field

from src.lib.logging import get_logger


logger = get_logger(__name__)


class FrequencyCaps(BaseModel):
    """
    Frequency cap configuration for outreach messages.
    
    Based on research.md CL-001:
    - Customers: ≤ 2 outreach messages/week
    - Workers (coaching): ≤ 1/week
    - Urgent alerts exempt with documented reason
    """
    
    # Customer limits (SmartEngage reminders)
    customer_daily_limit: int = Field(
        default=1,
        ge=0,
        le=10,
        description="Max outreach messages per customer per day"
    )
    customer_weekly_limit: int = Field(
        default=2,
        ge=0,
        le=20,
        description="Max outreach messages per customer per week (spec: ≤ 2)"
    )
    customer_minimum_hours_between: int = Field(
        default=24,
        ge=1,
        le=168,
        description="Minimum hours between messages to same customer"
    )
    
    # Worker limits (CoachNova coaching)
    worker_daily_limit: int = Field(
        default=1,
        ge=0,
        le=5,
        description="Max coaching messages per worker per day"
    )
    worker_weekly_limit: int = Field(
        default=1,
        ge=0,
        le=10,
        description="Max coaching messages per worker per week (spec: ≤ 1)"
    )
    worker_minimum_hours_between: int = Field(
        default=72,
        ge=1,
        le=168,
        description="Minimum hours between coaching messages to same worker"
    )
    
    # Channel-specific overrides (optional)
    sms_daily_limit: Optional[int] = Field(
        default=None,
        ge=0,
        le=10,
        description="Override daily limit for SMS channel"
    )
    sms_weekly_limit: Optional[int] = Field(
        default=None,
        ge=0,
        le=20,
        description="Override weekly limit for SMS channel"
    )
    
    email_daily_limit: Optional[int] = Field(
        default=None,
        ge=0,
        le=10,
        description="Override daily limit for email channel"
    )
    email_weekly_limit: Optional[int] = Field(
        default=None,
        ge=0,
        le=20,
        description="Override weekly limit for email channel"
    )
    
    push_daily_limit: Optional[int] = Field(
        default=None,
        ge=0,
        le=20,
        description="Override daily limit for push notifications"
    )
    push_weekly_limit: Optional[int] = Field(
        default=None,
        ge=0,
        le=50,
        description="Override weekly limit for push notifications"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "customer_daily_limit": 1,
                "customer_weekly_limit": 2,
                "customer_minimum_hours_between": 24,
                "worker_daily_limit": 1,
                "worker_weekly_limit": 1,
                "worker_minimum_hours_between": 72,
            }
        }


class FeatureFlags(BaseModel):
    """Feature flags for enabling/disabling functionality."""
    
    smartengage_enabled: bool = Field(
        default=True,
        description="Enable SmartEngage customer reminders"
    )
    coachnova_enabled: bool = Field(
        default=True,
        description="Enable CoachNova worker coaching"
    )
    ai_generation_enabled: bool = Field(
        default=True,
        description="Enable AI message generation (fallback to templates if disabled)"
    )
    safety_filter_enabled: bool = Field(
        default=True,
        description="Enable safety filter for AI-generated content"
    )
    deeplink_enabled: bool = Field(
        default=True,
        description="Enable deeplink generation in messages"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "smartengage_enabled": True,
                "coachnova_enabled": True,
                "ai_generation_enabled": True,
                "safety_filter_enabled": True,
                "deeplink_enabled": True,
            }
        }


class CampaignPresets(BaseModel):
    """Preset configurations for different campaign types."""
    
    default_cadence_days: int = Field(default=21, ge=7, le=90)
    default_batch_size: int = Field(default=50, ge=1, le=1000)
    default_send_window_start: int = Field(default=9, ge=0, le=23)
    default_send_window_end: int = Field(default=18, ge=0, le=23)
    
    aggressive_cadence_days: int = Field(default=14, ge=7, le=90)
    aggressive_batch_size: int = Field(default=100, ge=1, le=1000)
    
    gentle_cadence_days: int = Field(default=30, ge=7, le=90)
    gentle_batch_size: int = Field(default=25, ge=1, le=1000)
    
    class Config:
        json_schema_extra = {
            "example": {
                "default_cadence_days": 21,
                "default_batch_size": 50,
                "aggressive_cadence_days": 14,
                "gentle_cadence_days": 30,
            }
        }


# Global configuration instances (can be overridden)
_frequency_caps: Optional[FrequencyCaps] = None
_feature_flags: Optional[FeatureFlags] = None
_campaign_presets: Optional[CampaignPresets] = None


def get_frequency_caps() -> FrequencyCaps:
    """
    Get frequency caps configuration.
    
    Returns:
        FrequencyCaps instance with current settings
    """
    global _frequency_caps
    if _frequency_caps is None:
        _frequency_caps = FrequencyCaps()
        logger.info("Initialized default frequency caps configuration")
    return _frequency_caps


def set_frequency_caps(caps: FrequencyCaps) -> None:
    """
    Override frequency caps configuration.
    
    Args:
        caps: New FrequencyCaps configuration
    """
    global _frequency_caps
    _frequency_caps = caps
    logger.info("Updated frequency caps configuration", extra={
        "customer_weekly": caps.customer_weekly_limit,
        "worker_weekly": caps.worker_weekly_limit,
    })


def get_feature_flags() -> FeatureFlags:
    """Get feature flags configuration."""
    global _feature_flags
    if _feature_flags is None:
        _feature_flags = FeatureFlags()
        logger.info("Initialized default feature flags")
    return _feature_flags


def set_feature_flags(flags: FeatureFlags) -> None:
    """Override feature flags configuration."""
    global _feature_flags
    _feature_flags = flags
    logger.info("Updated feature flags")


def get_campaign_presets() -> CampaignPresets:
    """Get campaign presets configuration."""
    global _campaign_presets
    if _campaign_presets is None:
        _campaign_presets = CampaignPresets()
        logger.info("Initialized default campaign presets")
    return _campaign_presets


def set_campaign_presets(presets: CampaignPresets) -> None:
    """Override campaign presets configuration."""
    global _campaign_presets
    _campaign_presets = presets
    logger.info("Updated campaign presets")


def reset_all_configs() -> None:
    """Reset all configurations to defaults (useful for testing)."""
    global _frequency_caps, _feature_flags, _campaign_presets
    _frequency_caps = None
    _feature_flags = None
    _campaign_presets = None
    logger.info("Reset all configurations to defaults")

"""
Unit tests for config_flags module.
"""
import pytest

from src.lib.config_flags import (
    FrequencyCaps,
    FeatureFlags,
    CampaignPresets,
    get_frequency_caps,
    set_frequency_caps,
    get_feature_flags,
    set_feature_flags,
    get_campaign_presets,
    set_campaign_presets,
    reset_all_configs,
)


@pytest.mark.unit
def test_frequency_caps_defaults():
    """FrequencyCaps should have spec-compliant defaults."""
    caps = FrequencyCaps()
    
    # Customer limits (spec: ≤ 2/week)
    assert caps.customer_daily_limit == 1
    assert caps.customer_weekly_limit == 2
    assert caps.customer_minimum_hours_between == 24
    
    # Worker limits (spec: ≤ 1/week)
    assert caps.worker_daily_limit == 1
    assert caps.worker_weekly_limit == 1
    assert caps.worker_minimum_hours_between == 72


@pytest.mark.unit
def test_frequency_caps_custom_values():
    """FrequencyCaps should accept custom values."""
    caps = FrequencyCaps(
        customer_daily_limit=2,
        customer_weekly_limit=5,
        worker_daily_limit=1,
        worker_weekly_limit=2,
    )
    
    assert caps.customer_daily_limit == 2
    assert caps.customer_weekly_limit == 5
    assert caps.worker_weekly_limit == 2


@pytest.mark.unit
def test_frequency_caps_validation():
    """FrequencyCaps should validate ranges."""
    # Valid values
    caps = FrequencyCaps(customer_daily_limit=5)
    assert caps.customer_daily_limit == 5
    
    # Out of range values should raise validation error
    with pytest.raises(ValueError):
        FrequencyCaps(customer_daily_limit=100)  # Max is 10
    
    with pytest.raises(ValueError):
        FrequencyCaps(customer_daily_limit=-1)  # Min is 0


@pytest.mark.unit
def test_frequency_caps_channel_overrides():
    """FrequencyCaps should support channel-specific overrides."""
    caps = FrequencyCaps(
        customer_weekly_limit=2,
        sms_weekly_limit=1,  # Stricter for SMS
        email_weekly_limit=3,  # More relaxed for email
    )
    
    assert caps.customer_weekly_limit == 2
    assert caps.sms_weekly_limit == 1
    assert caps.email_weekly_limit == 3


@pytest.mark.unit
def test_feature_flags_defaults():
    """FeatureFlags should default to enabled."""
    flags = FeatureFlags()
    
    assert flags.smartengage_enabled is True
    assert flags.coachnova_enabled is True
    assert flags.ai_generation_enabled is True
    assert flags.safety_filter_enabled is True
    assert flags.deeplink_enabled is True


@pytest.mark.unit
def test_feature_flags_custom():
    """FeatureFlags should accept custom values."""
    flags = FeatureFlags(
        smartengage_enabled=False,
        ai_generation_enabled=False,
    )
    
    assert flags.smartengage_enabled is False
    assert flags.ai_generation_enabled is False
    assert flags.coachnova_enabled is True  # Not overridden


@pytest.mark.unit
def test_campaign_presets_defaults():
    """CampaignPresets should have reasonable defaults."""
    presets = CampaignPresets()
    
    assert presets.default_cadence_days == 21
    assert presets.default_batch_size == 50
    assert presets.aggressive_cadence_days == 14
    assert presets.gentle_cadence_days == 30


@pytest.mark.unit
def test_get_frequency_caps_singleton():
    """get_frequency_caps() should return same instance."""
    reset_all_configs()  # Clean state
    
    caps1 = get_frequency_caps()
    caps2 = get_frequency_caps()
    
    assert caps1 is caps2


@pytest.mark.unit
def test_set_frequency_caps():
    """set_frequency_caps() should override global config."""
    reset_all_configs()
    
    custom_caps = FrequencyCaps(
        customer_weekly_limit=5,
        worker_weekly_limit=3,
    )
    
    set_frequency_caps(custom_caps)
    
    retrieved_caps = get_frequency_caps()
    assert retrieved_caps.customer_weekly_limit == 5
    assert retrieved_caps.worker_weekly_limit == 3


@pytest.mark.unit
def test_get_feature_flags():
    """get_feature_flags() should return configuration."""
    reset_all_configs()
    
    flags = get_feature_flags()
    
    assert flags.smartengage_enabled is True
    assert isinstance(flags, FeatureFlags)


@pytest.mark.unit
def test_set_feature_flags():
    """set_feature_flags() should override global config."""
    reset_all_configs()
    
    custom_flags = FeatureFlags(
        smartengage_enabled=False,
        safety_filter_enabled=False,
    )
    
    set_feature_flags(custom_flags)
    
    retrieved_flags = get_feature_flags()
    assert retrieved_flags.smartengage_enabled is False
    assert retrieved_flags.safety_filter_enabled is False


@pytest.mark.unit
def test_get_campaign_presets():
    """get_campaign_presets() should return configuration."""
    reset_all_configs()
    
    presets = get_campaign_presets()
    
    assert presets.default_cadence_days == 21
    assert isinstance(presets, CampaignPresets)


@pytest.mark.unit
def test_set_campaign_presets():
    """set_campaign_presets() should override global config."""
    reset_all_configs()
    
    custom_presets = CampaignPresets(
        default_cadence_days=28,
        aggressive_cadence_days=10,
    )
    
    set_campaign_presets(custom_presets)
    
    retrieved_presets = get_campaign_presets()
    assert retrieved_presets.default_cadence_days == 28
    assert retrieved_presets.aggressive_cadence_days == 10


@pytest.mark.unit
def test_reset_all_configs():
    """reset_all_configs() should clear all overrides."""
    # Set custom configs
    set_frequency_caps(FrequencyCaps(customer_weekly_limit=10))
    set_feature_flags(FeatureFlags(smartengage_enabled=False))
    set_campaign_presets(CampaignPresets(default_cadence_days=14))
    
    # Reset
    reset_all_configs()
    
    # Should get new default instances
    caps = get_frequency_caps()
    flags = get_feature_flags()
    presets = get_campaign_presets()
    
    assert caps.customer_weekly_limit == 2  # Back to default
    assert flags.smartengage_enabled is True  # Back to default
    assert presets.default_cadence_days == 21  # Back to default


@pytest.mark.unit
def test_frequency_caps_minimum_hours_validation():
    """Minimum hours between messages should be validated."""
    caps = FrequencyCaps(customer_minimum_hours_between=48)
    assert caps.customer_minimum_hours_between == 48
    
    # Out of range
    with pytest.raises(ValueError):
        FrequencyCaps(customer_minimum_hours_between=200)  # Max is 168 (1 week)
    
    with pytest.raises(ValueError):
        FrequencyCaps(customer_minimum_hours_between=0)  # Min is 1

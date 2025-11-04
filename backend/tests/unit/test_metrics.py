"""
Unit tests for metrics collection and Prometheus export.
"""

import pytest
from src.lib.metrics import MetricsCollector, get_metrics_collector, reset_metrics


@pytest.fixture
def metrics():
    """Fresh metrics collector for each test."""
    collector = MetricsCollector()
    return collector


@pytest.mark.unit
def test_metrics_collector_initialization(metrics):
    """Test metrics collector initializes with empty counters."""
    output = metrics.export_prometheus()
    assert output == ""  # No metrics yet


@pytest.mark.unit
def test_increment_sends_basic(metrics):
    """Test incrementing send counter."""
    metrics.increment_sends(
        agent_type="smartengage",
        channel="SMS",
        message_type="REMINDER"
    )
    
    value = metrics.get_counter_value(
        "ai_messages_sent_total",
        {
            "agent_type": "smartengage",
            "channel": "SMS",
            "message_type": "REMINDER",
            "status": "sent"
        }
    )
    assert value == 1


@pytest.mark.unit
def test_increment_sends_multiple(metrics):
    """Test incrementing send counter multiple times."""
    metrics.increment_sends("smartengage", "SMS", "REMINDER", amount=5)
    metrics.increment_sends("smartengage", "SMS", "REMINDER", amount=3)
    
    value = metrics.get_counter_value(
        "ai_messages_sent_total",
        {
            "agent_type": "smartengage",
            "channel": "SMS",
            "message_type": "REMINDER",
            "status": "sent"
        }
    )
    assert value == 8


@pytest.mark.unit
def test_increment_sends_different_labels(metrics):
    """Test counters are separate for different label combinations."""
    metrics.increment_sends("smartengage", "SMS", "REMINDER")
    metrics.increment_sends("smartengage", "EMAIL", "REMINDER")
    metrics.increment_sends("coachnova", "SMS", "COACHING")
    
    # Verify each counter is independent
    sms_reminder = metrics.get_counter_value(
        "ai_messages_sent_total",
        {"agent_type": "smartengage", "channel": "SMS", "message_type": "REMINDER", "status": "sent"}
    )
    email_reminder = metrics.get_counter_value(
        "ai_messages_sent_total",
        {"agent_type": "smartengage", "channel": "EMAIL", "message_type": "REMINDER", "status": "sent"}
    )
    coaching = metrics.get_counter_value(
        "ai_messages_sent_total",
        {"agent_type": "coachnova", "channel": "SMS", "message_type": "COACHING", "status": "sent"}
    )
    
    assert sms_reminder == 1
    assert email_reminder == 1
    assert coaching == 1


@pytest.mark.unit
def test_increment_opens(metrics):
    """Test incrementing opens counter."""
    metrics.increment_opens("smartengage", "SMS", source="app")
    metrics.increment_opens("smartengage", "SMS", source="app")
    
    value = metrics.get_counter_value(
        "user_events_total",
        {
            "event_type": "notification_opened",
            "agent_type": "smartengage",
            "channel": "SMS",
            "source": "app"
        }
    )
    assert value == 2


@pytest.mark.unit
def test_increment_clicks(metrics):
    """Test incrementing clicks counter."""
    metrics.increment_clicks("smartengage", "EMAIL", source="web")
    
    value = metrics.get_counter_value(
        "user_events_total",
        {
            "event_type": "message_clicked",
            "agent_type": "smartengage",
            "channel": "EMAIL",
            "source": "web"
        }
    )
    assert value == 1


@pytest.mark.unit
def test_increment_conversions(metrics):
    """Test incrementing conversions counter."""
    metrics.increment_conversions("smartengage", "SMS", conversion_type="booking_created")
    metrics.increment_conversions("smartengage", "SMS", conversion_type="booking_created")
    metrics.increment_conversions("smartengage", "SMS", conversion_type="booking_created")
    
    value = metrics.get_counter_value(
        "user_events_total",
        {
            "event_type": "booking_created",
            "agent_type": "smartengage",
            "channel": "SMS"
        }
    )
    assert value == 3


@pytest.mark.unit
def test_increment_delivered(metrics):
    """Test incrementing delivered counter."""
    metrics.increment_delivered("smartengage", "SMS", amount=10)
    
    value = metrics.get_counter_value(
        "ai_messages_delivered_total",
        {"agent_type": "smartengage", "channel": "SMS"}
    )
    assert value == 10


@pytest.mark.unit
def test_increment_failed(metrics):
    """Test incrementing failed counter."""
    metrics.increment_failed("smartengage", "SMS", reason="invalid_phone")
    
    value = metrics.get_counter_value(
        "ai_messages_failed_total",
        {"agent_type": "smartengage", "channel": "SMS", "reason": "invalid_phone"}
    )
    assert value == 1


@pytest.mark.unit
def test_increment_opt_outs(metrics):
    """Test incrementing opt-outs counter."""
    metrics.increment_opt_outs("SMS", reason="user_request")
    metrics.increment_opt_outs("SMS", reason="frequency_fatigue")
    
    user_request = metrics.get_counter_value(
        "opt_outs_total",
        {"channel": "SMS", "reason": "user_request"}
    )
    frequency = metrics.get_counter_value(
        "opt_outs_total",
        {"channel": "SMS", "reason": "frequency_fatigue"}
    )
    
    assert user_request == 1
    assert frequency == 1


@pytest.mark.unit
def test_export_prometheus_format(metrics):
    """Test Prometheus export format is correct."""
    metrics.increment_sends("smartengage", "SMS", "REMINDER")
    metrics.increment_opens("smartengage", "SMS", source="app")
    
    output = metrics.export_prometheus()
    
    # Verify HELP and TYPE comments
    assert "# HELP ai_messages_sent_total" in output
    assert "# TYPE ai_messages_sent_total counter" in output
    assert "# HELP user_events_total" in output
    assert "# TYPE user_events_total counter" in output
    
    # Verify metric lines
    assert 'ai_messages_sent_total{agent_type="smartengage",channel="SMS",message_type="REMINDER",status="sent"} 1' in output
    assert 'user_events_total{agent_type="smartengage",channel="SMS",event_type="notification_opened",source="app"} 1' in output


@pytest.mark.unit
def test_export_prometheus_multiple_metrics(metrics):
    """Test Prometheus export with multiple metric types."""
    metrics.increment_sends("smartengage", "SMS", "REMINDER", amount=5)
    metrics.increment_delivered("smartengage", "SMS", amount=4)
    metrics.increment_failed("smartengage", "SMS", reason="bounced", amount=1)
    metrics.increment_opens("smartengage", "SMS", source="app", amount=3)
    metrics.increment_clicks("smartengage", "SMS", source="app", amount=2)
    metrics.increment_conversions("smartengage", "SMS", amount=1)
    metrics.increment_opt_outs("SMS", reason="user_request")
    
    output = metrics.export_prometheus()
    
    # Verify all metric types present
    assert "ai_messages_sent_total" in output
    assert "ai_messages_delivered_total" in output
    assert "ai_messages_failed_total" in output
    assert "user_events_total" in output
    assert "opt_outs_total" in output
    
    # Verify values
    assert '} 5' in output  # sends
    assert '} 4' in output  # delivered
    assert '} 3' in output  # opens
    assert '} 2' in output  # clicks


@pytest.mark.unit
def test_export_prometheus_labels_sorted(metrics):
    """Test Prometheus export sorts labels alphabetically."""
    metrics.increment_sends("smartengage", "SMS", "REMINDER")
    
    output = metrics.export_prometheus()
    
    # Labels should be sorted: agent_type, channel, message_type, status
    assert 'agent_type="smartengage",channel="SMS",message_type="REMINDER",status="sent"' in output


@pytest.mark.unit
def test_reset_all_clears_counters(metrics):
    """Test reset_all clears all counters."""
    metrics.increment_sends("smartengage", "SMS", "REMINDER", amount=100)
    metrics.increment_opens("smartengage", "SMS", amount=50)
    
    # Verify counters exist
    assert metrics.get_counter_value("ai_messages_sent_total", {"agent_type": "smartengage", "channel": "SMS", "message_type": "REMINDER", "status": "sent"}) == 100
    
    # Reset
    metrics.reset_all()
    
    # Verify counters are cleared
    assert metrics.get_counter_value("ai_messages_sent_total", {"agent_type": "smartengage", "channel": "SMS", "message_type": "REMINDER", "status": "sent"}) == 0
    output = metrics.export_prometheus()
    assert output == ""


@pytest.mark.unit
def test_get_metrics_collector_singleton():
    """Test get_metrics_collector returns singleton instance."""
    collector1 = get_metrics_collector()
    collector2 = get_metrics_collector()
    
    assert collector1 is collector2
    
    # Increment on one affects the other
    collector1.increment_sends("smartengage", "SMS", "REMINDER")
    value = collector2.get_counter_value("ai_messages_sent_total", {"agent_type": "smartengage", "channel": "SMS", "message_type": "REMINDER", "status": "sent"})
    assert value == 1


@pytest.mark.unit
def test_reset_metrics_clears_singleton():
    """Test reset_metrics clears the global singleton."""
    collector = get_metrics_collector()
    collector.increment_sends("smartengage", "SMS", "REMINDER", amount=100)
    
    reset_metrics()
    
    # Verify cleared
    collector_after = get_metrics_collector()
    value = collector_after.get_counter_value("ai_messages_sent_total", {"agent_type": "smartengage", "channel": "SMS", "message_type": "REMINDER", "status": "sent"})
    assert value == 0


@pytest.mark.unit
def test_case_normalization(metrics):
    """Test metrics normalize case for consistency."""
    # Mix upper/lower case inputs
    metrics.increment_sends("SmartEngage", "sms", "reminder")
    
    # Should be normalized to lowercase agent_type, uppercase channel/message_type
    value = metrics.get_counter_value(
        "ai_messages_sent_total",
        {"agent_type": "smartengage", "channel": "SMS", "message_type": "REMINDER", "status": "sent"}
    )
    assert value == 1


@pytest.mark.unit
def test_nonexistent_counter_returns_zero(metrics):
    """Test getting nonexistent counter returns 0."""
    value = metrics.get_counter_value(
        "ai_messages_sent_total",
        {"agent_type": "nonexistent", "channel": "SMS", "message_type": "REMINDER", "status": "sent"}
    )
    assert value == 0

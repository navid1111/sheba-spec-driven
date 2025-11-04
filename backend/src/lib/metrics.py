"""
Prometheus-compatible metrics for observability.

Tracks key performance indicators:
- Message sends (by agent_type, channel, message_type, status)
- User interactions (opens, clicks, conversions)
- Opt-outs and errors
- Delivery status tracking

Usage:
    from src.lib.metrics import get_metrics_collector
    
    metrics = get_metrics_collector()
    metrics.increment_sends(agent_type="smartengage", channel="SMS", message_type="REMINDER")
    metrics.increment_opens(agent_type="smartengage", channel="SMS")
    metrics.increment_clicks(agent_type="smartengage", channel="SMS")
    
    # Export for Prometheus
    prometheus_output = metrics.export_prometheus()
"""

from typing import Dict, Tuple
from threading import Lock
from dataclasses import dataclass, field


@dataclass
class MetricCounter:
    """Thread-safe counter with labels."""
    
    value: int = 0
    labels: Dict[str, str] = field(default_factory=dict)
    
    def increment(self, amount: int = 1):
        """Increment counter by amount."""
        self.value += amount


class MetricsCollector:
    """
    Prometheus-style metrics collector for ShoktiAI observability.
    
    Counters:
    - ai_messages_sent_total: Messages sent by agent (labels: agent_type, channel, message_type, status)
    - ai_messages_delivered_total: Successfully delivered messages
    - ai_messages_failed_total: Failed deliveries
    - user_events_total: User interactions (labels: event_type, source, agent_type, channel)
    - opt_outs_total: User opt-outs (labels: channel, reason)
    
    Thread-safe for concurrent increments.
    """
    
    def __init__(self):
        self._lock = Lock()
        
        # Counters: key = (metric_name, labels_tuple), value = count
        self._counters: Dict[Tuple[str, Tuple[Tuple[str, str], ...]], int] = {}
    
    def _get_counter_key(self, metric_name: str, labels: Dict[str, str]) -> Tuple[str, Tuple[Tuple[str, str], ...]]:
        """Generate unique key for counter with sorted labels."""
        sorted_labels = tuple(sorted(labels.items()))
        return (metric_name, sorted_labels)
    
    def _increment(self, metric_name: str, labels: Dict[str, str], amount: int = 1):
        """Thread-safe increment of counter."""
        key = self._get_counter_key(metric_name, labels)
        with self._lock:
            self._counters[key] = self._counters.get(key, 0) + amount
    
    def _get_value(self, metric_name: str, labels: Dict[str, str]) -> int:
        """Get current value of counter."""
        key = self._get_counter_key(metric_name, labels)
        with self._lock:
            return self._counters.get(key, 0)
    
    # ===== Message Send Metrics =====
    
    def increment_sends(
        self,
        agent_type: str,
        channel: str,
        message_type: str,
        status: str = "sent",
        amount: int = 1
    ):
        """
        Increment messages sent counter.
        
        Args:
            agent_type: AI agent type (smartengage, coachnova)
            channel: Communication channel (SMS, EMAIL, PUSH)
            message_type: Message type (REMINDER, COACHING, PROMO)
            status: Send status (sent, delivered, failed, bounced)
            amount: Increment amount (default 1)
        """
        labels = {
            "agent_type": agent_type.lower(),
            "channel": channel.upper(),
            "message_type": message_type.upper(),
            "status": status.lower()
        }
        self._increment("ai_messages_sent_total", labels, amount)
    
    def increment_delivered(self, agent_type: str, channel: str, amount: int = 1):
        """Increment successfully delivered messages."""
        labels = {
            "agent_type": agent_type.lower(),
            "channel": channel.upper()
        }
        self._increment("ai_messages_delivered_total", labels, amount)
    
    def increment_failed(self, agent_type: str, channel: str, reason: str = "unknown", amount: int = 1):
        """Increment failed message deliveries."""
        labels = {
            "agent_type": agent_type.lower(),
            "channel": channel.upper(),
            "reason": reason.lower()
        }
        self._increment("ai_messages_failed_total", labels, amount)
    
    # ===== User Interaction Metrics =====
    
    def increment_opens(self, agent_type: str, channel: str, source: str = "unknown", amount: int = 1):
        """
        Increment message opens counter.
        
        Args:
            agent_type: AI agent type
            channel: Communication channel
            source: Event source (push, sms, app, web)
            amount: Increment amount
        """
        labels = {
            "event_type": "notification_opened",
            "agent_type": agent_type.lower(),
            "channel": channel.upper(),
            "source": source.lower()
        }
        self._increment("user_events_total", labels, amount)
    
    def increment_clicks(self, agent_type: str, channel: str, source: str = "unknown", amount: int = 1):
        """
        Increment message clicks counter.
        
        Args:
            agent_type: AI agent type
            channel: Communication channel
            source: Event source (push, sms, app, web)
            amount: Increment amount
        """
        labels = {
            "event_type": "message_clicked",
            "agent_type": agent_type.lower(),
            "channel": channel.upper(),
            "source": source.lower()
        }
        self._increment("user_events_total", labels, amount)
    
    def increment_conversions(
        self,
        agent_type: str,
        channel: str,
        conversion_type: str = "booking_created",
        amount: int = 1
    ):
        """
        Increment conversions counter (bookings created from messages).
        
        Args:
            agent_type: AI agent type
            channel: Communication channel
            conversion_type: Type of conversion (booking_created, deeplink_followed)
            amount: Increment amount
        """
        labels = {
            "event_type": conversion_type.lower(),
            "agent_type": agent_type.lower(),
            "channel": channel.upper()
        }
        self._increment("user_events_total", labels, amount)
    
    def increment_opt_outs(self, channel: str, reason: str = "user_request", amount: int = 1):
        """
        Increment opt-outs counter.
        
        Args:
            channel: Communication channel
            reason: Opt-out reason (user_request, frequency_fatigue, spam_report)
            amount: Increment amount
        """
        labels = {
            "channel": channel.upper(),
            "reason": reason.lower()
        }
        self._increment("opt_outs_total", labels, amount)
    
    # ===== Export =====
    
    def export_prometheus(self) -> str:
        """
        Export all metrics in Prometheus text format.
        
        Returns:
            Prometheus-compatible text output
        """
        output_lines = []
        
        # Group counters by metric name
        metrics_by_name: Dict[str, list] = {}
        with self._lock:
            for (metric_name, labels_tuple), value in self._counters.items():
                if metric_name not in metrics_by_name:
                    metrics_by_name[metric_name] = []
                metrics_by_name[metric_name].append((dict(labels_tuple), value))
        
        # Generate Prometheus format for each metric
        for metric_name in sorted(metrics_by_name.keys()):
            # Add HELP and TYPE comments
            help_text = self._get_help_text(metric_name)
            output_lines.append(f"# HELP {metric_name} {help_text}")
            output_lines.append(f"# TYPE {metric_name} counter")
            
            # Add metric lines
            for labels_dict, value in sorted(metrics_by_name[metric_name], key=lambda x: str(x[0])):
                labels_str = ",".join([f'{k}="{v}"' for k, v in sorted(labels_dict.items())])
                output_lines.append(f"{metric_name}{{{labels_str}}} {value}")
            
            output_lines.append("")  # Blank line between metrics
        
        return "\n".join(output_lines)
    
    def _get_help_text(self, metric_name: str) -> str:
        """Get help text for metric."""
        help_texts = {
            "ai_messages_sent_total": "Total number of AI-generated messages sent",
            "ai_messages_delivered_total": "Total number of messages successfully delivered",
            "ai_messages_failed_total": "Total number of failed message deliveries",
            "user_events_total": "Total number of user interaction events",
            "opt_outs_total": "Total number of user opt-outs from messaging"
        }
        return help_texts.get(metric_name, "Counter metric")
    
    def get_counter_value(self, metric_name: str, labels: Dict[str, str]) -> int:
        """
        Get current value of a specific counter.
        
        Args:
            metric_name: Name of the metric
            labels: Label filters
        
        Returns:
            Current counter value
        """
        return self._get_value(metric_name, labels)
    
    def reset_all(self):
        """Reset all counters (for testing)."""
        with self._lock:
            self._counters.clear()


# Global singleton instance
_metrics_collector: MetricsCollector | None = None
_metrics_lock = Lock()


def get_metrics_collector() -> MetricsCollector:
    """
    Get global metrics collector singleton.
    
    Returns:
        MetricsCollector instance
    """
    global _metrics_collector
    if _metrics_collector is None:
        with _metrics_lock:
            if _metrics_collector is None:
                _metrics_collector = MetricsCollector()
    return _metrics_collector


def reset_metrics():
    """Reset global metrics collector (for testing)."""
    global _metrics_collector
    with _metrics_lock:
        if _metrics_collector is not None:
            _metrics_collector.reset_all()

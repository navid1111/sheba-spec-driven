"""
SQLAlchemy models package.
Import all models here to ensure they're registered with Base.metadata.
"""
from src.models.users import User
from src.models.workers import Worker
from src.models.customers import Customer
from src.models.services import Service
from src.models.bookings import Booking
from src.models.reviews import Review
from src.models.ai_message_templates import AIMessageTemplate
from src.models.ai_messages import AIMessage
from src.models.user_activity_events import UserActivityEvent
from src.models.jobs import Job
from src.models.campaigns import Campaign

__all__ = [
    "User",
    "Worker",
    "Customer",
    "Service",
    "Booking",
    "Review",
    "AIMessageTemplate",
    "AIMessage",
    "UserActivityEvent",
    "Job",
    "Campaign",
]

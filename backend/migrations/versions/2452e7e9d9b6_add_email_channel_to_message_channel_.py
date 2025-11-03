"""add_email_channel_to_message_channel_enum

Revision ID: 2452e7e9d9b6
Revises: 2b4c870d426d
Create Date: 2025-11-04 03:02:53.895217

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2452e7e9d9b6'
down_revision: Union[str, Sequence[str], None] = '2b4c870d426d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema: Add EMAIL to MessageChannel enum."""
    # Add 'EMAIL' to the message_channel enum
    op.execute("ALTER TYPE message_channel ADD VALUE IF NOT EXISTS 'EMAIL'")


def downgrade() -> None:
    """Downgrade schema: Cannot remove enum value in PostgreSQL."""
    # PostgreSQL doesn't support removing enum values
    # This is a one-way migration
    pass

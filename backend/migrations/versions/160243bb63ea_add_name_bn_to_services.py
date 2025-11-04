"""add_name_bn_to_services

Revision ID: 160243bb63ea
Revises: 2452e7e9d9b6
Create Date: 2025-11-04 21:35:02.553096

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '160243bb63ea'
down_revision: Union[str, Sequence[str], None] = '2452e7e9d9b6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add name_bn column to services table
    op.add_column('services', sa.Column('name_bn', sa.String(length=255), nullable=True, comment='Service name in Bengali'))


def downgrade() -> None:
    """Downgrade schema."""
    # Remove name_bn column from services table
    op.drop_column('services', 'name_bn')

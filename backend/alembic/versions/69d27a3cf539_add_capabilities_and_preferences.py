"""add_capabilities_and_preferences

Revision ID: 69d27a3cf539
Revises: 
Create Date: 2026-01-22 02:02:48.912502

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '69d27a3cf539'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Postgres suporta JSONB nativamente e DEFAULTs em ADD COLUMN
    op.add_column('model_catalog', sa.Column('capabilities', sa.JSON(), server_default='["text_input"]', nullable=False))
    op.add_column('user_profiles', sa.Column('model_preferences', sa.JSON(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('user_profiles', 'model_preferences')
    op.drop_column('model_catalog', 'capabilities')

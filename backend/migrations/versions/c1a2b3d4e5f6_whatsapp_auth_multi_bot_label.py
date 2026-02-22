"""whatsapp_auth: remove unique on user_id, add label column

Revision ID: c1a2b3d4e5f6
Revises: b908617bfbf7
Create Date: 2026-02-21 18:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c1a2b3d4e5f6'
down_revision: Union[str, None] = 'b908617bfbf7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add label column
    op.add_column('whatsapp_auth', sa.Column('label', sa.String(length=50), nullable=True))
    # Remove unique constraint on user_id to allow multiple bots per admin
    op.drop_constraint('whatsapp_auth_user_id_key', 'whatsapp_auth', type_='unique')
    # Add index on user_id for fast lookups
    op.create_index('ix_whatsapp_auth_user_id', 'whatsapp_auth', ['user_id'])


def downgrade() -> None:
    op.drop_index('ix_whatsapp_auth_user_id', table_name='whatsapp_auth')
    op.create_unique_constraint('whatsapp_auth_user_id_key', 'whatsapp_auth', ['user_id'])
    op.drop_column('whatsapp_auth', 'label')

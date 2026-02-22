"""add knowledge_documents table and index_status to dispute_documents

Revision ID: d2e3f4a5b6c7
Revises: c1a2b3d4e5f6
Create Date: 2026-02-21 20:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision: str = 'd2e3f4a5b6c7'
down_revision: Union[str, None] = 'c1a2b3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create knowledge_documents table
    op.create_table(
        'knowledge_documents',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('filename', sa.String(255), nullable=False),
        sa.Column('original_filename', sa.String(255), nullable=False),
        sa.Column('file_url', sa.String(500), nullable=False),
        sa.Column('file_size', sa.Integer, nullable=False, server_default='0'),
        sa.Column('doc_category', sa.String(30), nullable=False, server_default='other'),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('index_status', sa.String(20), nullable=False, server_default='pending'),
        sa.Column('index_error', sa.Text, nullable=True),
        sa.Column('chunk_count', sa.Integer, nullable=False, server_default='0'),
        sa.Column('uploaded_by', UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('ix_knowledge_documents_uploaded_by', 'knowledge_documents', ['uploaded_by'])

    # Add index_status column to dispute_documents
    op.add_column(
        'dispute_documents',
        sa.Column('index_status', sa.String(20), nullable=False, server_default='pending'),
    )


def downgrade() -> None:
    op.drop_column('dispute_documents', 'index_status')
    op.drop_index('ix_knowledge_documents_uploaded_by', table_name='knowledge_documents')
    op.drop_table('knowledge_documents')

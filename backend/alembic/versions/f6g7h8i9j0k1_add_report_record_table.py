"""add report_record table

Revision ID: f6g7h8i9j0k1
Revises: e5f6g7h8i9j0
Create Date: 2025-01-01 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = 'f6g7h8i9j0k1'
down_revision = 'e5f6g7h8i9j0'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'report_record',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('report_id', sa.String(length=36), nullable=False),
        sa.Column('event_id', sa.Integer(), nullable=False),
        sa.Column('event_name', sa.String(length=255), nullable=False),
        sa.Column('generated_at', sa.String(length=32), nullable=False),
        sa.Column('formats', sa.JSON(), nullable=False),
        sa.Column('files', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('report_id', name='uq_report_record_report_id'),
    )
    op.create_index('idx_rr_event_id', 'report_record', ['event_id'])
    op.create_index('idx_rr_generated_at', 'report_record', ['generated_at'])
    op.create_index('idx_rr_report_id', 'report_record', ['report_id'])


def downgrade() -> None:
    op.drop_index('idx_rr_report_id', table_name='report_record')
    op.drop_index('idx_rr_generated_at', table_name='report_record')
    op.drop_index('idx_rr_event_id', table_name='report_record')
    op.drop_table('report_record')
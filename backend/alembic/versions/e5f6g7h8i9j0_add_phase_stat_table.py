"""add phase_stat table

Revision ID: e5f6g7h8i9j0
Revises: d4e5f6g7h8i9
Create Date: 2025-01-01 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = 'e5f6g7h8i9j0'
down_revision = 'd4e5f6g7h8i9'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'phase_stat',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('match_id', sa.Integer(), nullable=False),
        sa.Column('team_id', sa.Integer(), nullable=False),
        sa.Column('phase', sa.String(length=16), nullable=False),
        sa.Column('distance_traveled_ft', sa.Float(), nullable=True),
        sa.Column('avg_velocity_fps', sa.Float(), nullable=True),
        sa.Column('max_velocity_fps', sa.Float(), nullable=True),
        sa.Column('time_in_scoring_zone_s', sa.Float(), nullable=True),
        sa.Column('estimated_score', sa.Float(), nullable=True),
        sa.Column('actions_detected', sa.JSON(), nullable=True),
        sa.Column('track_count', sa.Integer(), nullable=True),
        sa.Column('data_confidence', sa.String(length=16), nullable=True),
        sa.Column('computed_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['match_id'], ['match.match_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['team_id'], ['team.team_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('match_id', 'team_id', 'phase', name='uq_phase_stat_match_team_phase'),
    )
    op.create_index('idx_ps_match_id', 'phase_stat', ['match_id'])
    op.create_index('idx_ps_match_team', 'phase_stat', ['match_id', 'team_id'])
    op.create_index('idx_ps_team_id', 'phase_stat', ['team_id'])


def downgrade() -> None:
    op.drop_index('idx_ps_team_id', table_name='phase_stat')
    op.drop_index('idx_ps_match_team', table_name='phase_stat')
    op.drop_index('idx_ps_match_id', table_name='phase_stat')
    op.drop_table('phase_stat')
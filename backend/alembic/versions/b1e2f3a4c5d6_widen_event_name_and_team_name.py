"""widen event name and team name columns

Revision ID: b1e2f3a4c5d6
Revises: a3f1c8e92d04
Create Date: 2026-04-26 00:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'b1e2f3a4c5d6'
down_revision: Union[str, None] = 'a3f1c8e92d04'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # TBA event names can be very long (sponsors etc.) — use 255
    op.alter_column('event', 'name',
        existing_type=sa.String(length=120),
        type_=sa.String(length=255),
        existing_nullable=False,
    )
    # Team names can also exceed 120 chars
    op.alter_column('team', 'team_name',
        existing_type=sa.String(length=120),
        type_=sa.String(length=255),
        existing_nullable=True,
    )
    # School names too
    op.alter_column('team', 'school_name',
        existing_type=sa.String(length=200),
        type_=sa.String(length=255),
        existing_nullable=True,
    )


def downgrade() -> None:
    op.alter_column('team', 'school_name',
        existing_type=sa.String(length=255),
        type_=sa.String(length=200),
        existing_nullable=True,
    )
    op.alter_column('team', 'team_name',
        existing_type=sa.String(length=255),
        type_=sa.String(length=120),
        existing_nullable=True,
    )
    op.alter_column('event', 'name',
        existing_type=sa.String(length=255),
        type_=sa.String(length=120),
        existing_nullable=False,
    )
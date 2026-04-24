"""split event location into city state country

Revision ID: a3f1c8e92d04
Revises: 90d73322605e
Create Date: 2026-04-24 00:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'a3f1c8e92d04'
down_revision: Union[str, None] = '90d73322605e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('event', sa.Column('city', sa.String(length=100), nullable=True))
    op.add_column('event', sa.Column('state_prov', sa.String(length=60), nullable=True))
    op.add_column('event', sa.Column('country', sa.String(length=60), nullable=True))

    op.execute("""
        UPDATE event
        SET
            city       = split_part(location, ', ', 1),
            state_prov = CASE WHEN array_length(string_to_array(location, ', '), 1) >= 3
                              THEN split_part(location, ', ', 2)
                              ELSE NULL END,
            country    = split_part(location, ', ', array_length(string_to_array(location, ', '), 1))
        WHERE location IS NOT NULL
    """)

    op.drop_column('event', 'location')


def downgrade() -> None:
    op.add_column('event', sa.Column('location', sa.String(length=200), nullable=True))

    op.execute("""
        UPDATE event
        SET location = TRIM(BOTH ', ' FROM
            CONCAT_WS(', ',
                NULLIF(city, ''),
                NULLIF(state_prov, ''),
                NULLIF(country, '')
            )
        )
    """)

    op.drop_column('event', 'country')
    op.drop_column('event', 'state_prov')
    op.drop_column('event', 'city')

"""add movement_track and event_camera_calibration tables

Revision ID: d4e5f6g7h8i9
Revises: c2d3e4f5g6h7
Create Date: 2025-01-01 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = "d4e5f6g7h8i9"
down_revision = "c2d3e4f5g6h7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── event_camera_calibration ──────────────────────────────────────────────
    op.create_table(
        "event_camera_calibration",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "event_id",
            sa.Integer(),
            sa.ForeignKey("event.event_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("camera_position", sa.String(64), nullable=False),
        sa.Column("perspective_matrix", sa.JSON(), nullable=False),
        sa.Column(
            "calibrated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
        sa.Column("calibrated_by", sa.String(128), nullable=False),
        sa.Column("active", sa.Boolean(), default=True, nullable=False),
    )

    # ── movement_track ────────────────────────────────────────────────────────
    op.create_table(
        "movement_track",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "match_id",
            sa.Integer(),
            sa.ForeignKey("match.match_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "team_id",
            sa.Integer(),
            sa.ForeignKey("team.team_id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("track_id", sa.Integer(), nullable=False),
        # Position
        sa.Column("frame_number", sa.Integer(), nullable=False),
        sa.Column("timestamp_ms", sa.Integer(), nullable=False),
        sa.Column("pixel_x", sa.Float(), nullable=False),
        sa.Column("pixel_y", sa.Float(), nullable=False),
        sa.Column("field_x", sa.Float(), nullable=True),
        sa.Column("field_y", sa.Float(), nullable=True),
        # Bounding box
        sa.Column("bounding_box_width", sa.Float(), nullable=True),
        sa.Column("bounding_box_height", sa.Float(), nullable=True),
        sa.Column("bounding_box_size_change", sa.Float(), nullable=False, default=0.0),
        # Identification
        sa.Column(
            "identification_method",
            sa.String(64),
            nullable=False,
            default="UNKNOWN",
        ),
        sa.Column("confidence_score", sa.Float(), nullable=False, default=0.0),
        sa.Column("team_number_visible", sa.Boolean(), nullable=False, default=False),
        # Quality flags
        sa.Column("interpolated", sa.Boolean(), nullable=False, default=False),
        sa.Column("configuration_changed", sa.Boolean(), nullable=False, default=False),
        sa.Column("flagged_for_review", sa.Boolean(), nullable=False, default=False),
        sa.Column("review_reason", sa.String(128), nullable=True),
        sa.Column("manually_corrected", sa.Boolean(), nullable=False, default=False),
        sa.Column(
            "corrected_team_id",
            sa.Integer(),
            sa.ForeignKey("team.team_id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
    )

    # Indexes
    op.create_index("idx_mt_match_id", "movement_track", ["match_id"])
    op.create_index("idx_mt_team_id", "movement_track", ["team_id"])
    op.create_index("idx_mt_flagged", "movement_track", ["flagged_for_review"])
    op.create_index(
        "idx_mt_match_frame", "movement_track", ["match_id", "frame_number"]
    )


def downgrade() -> None:
    op.drop_index("idx_mt_match_frame", "movement_track")
    op.drop_index("idx_mt_flagged", "movement_track")
    op.drop_index("idx_mt_team_id", "movement_track")
    op.drop_index("idx_mt_match_id", "movement_track")
    op.drop_table("movement_track")
    op.drop_table("event_camera_calibration")
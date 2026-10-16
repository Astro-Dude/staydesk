"""create rooms table

Revision ID: 0001_create_rooms
Revises:
Create Date: 2026-10-16
"""

import sqlalchemy as sa
from alembic import op

revision = "0001_create_rooms"
down_revision = None
branch_labels = None
depends_on = None

ROOM_TYPES = ("SINGLE", "DOUBLE", "DELUXE", "SUITE")
HOUSEKEEPING = ("CLEAN", "DIRTY", "OUT_OF_SERVICE")


def upgrade() -> None:
    op.create_table(
        "rooms",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("number", sa.String(length=10), nullable=False),
        sa.Column(
            "room_type",
            sa.Enum(
                *ROOM_TYPES, name="room_type", native_enum=False, create_constraint=True, length=20
            ),
            nullable=False,
        ),
        sa.Column("floor", sa.Integer(), nullable=False),
        sa.Column("capacity", sa.Integer(), nullable=False),
        sa.Column("nightly_rate", sa.Integer(), nullable=False),
        sa.Column(
            "housekeeping",
            sa.Enum(
                *HOUSEKEEPING,
                name="housekeeping",
                native_enum=False,
                create_constraint=True,
                length=20,
            ),
            nullable=False,
            server_default="CLEAN",
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.UniqueConstraint("number", name="uq_rooms_number"),
        sa.CheckConstraint("capacity BETWEEN 1 AND 10", name="ck_rooms_capacity"),
        sa.CheckConstraint("nightly_rate > 0", name="ck_rooms_nightly_rate"),
        sa.CheckConstraint("floor >= 0", name="ck_rooms_floor"),
    )


def downgrade() -> None:
    op.drop_table("rooms")

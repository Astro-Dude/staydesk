"""create reservations table

Revision ID: 0002_create_reservations
Revises: 0001_create_rooms
Create Date: 2026-10-16
"""

import sqlalchemy as sa
from alembic import op

revision = "0002_create_reservations"
down_revision = "0001_create_rooms"
branch_labels = None
depends_on = None

STATUSES = ("BOOKED", "CHECKED_IN", "CHECKED_OUT", "CANCELLED")


def upgrade() -> None:
    op.create_table(
        "reservations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "room_id",
            sa.Integer(),
            sa.ForeignKey("rooms.id", ondelete="CASCADE", name="fk_reservations_room_id"),
            nullable=False,
        ),
        sa.Column("guest_name", sa.String(length=120), nullable=False),
        sa.Column("guest_email", sa.String(length=255), nullable=False),
        sa.Column("guest_phone", sa.String(length=30), nullable=False, server_default=""),
        sa.Column("guests", sa.Integer(), nullable=False),
        sa.Column("check_in", sa.Date(), nullable=False),
        sa.Column("check_out", sa.Date(), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                *STATUSES,
                name="reservation_status",
                native_enum=False,
                create_constraint=True,
                length=20,
            ),
            nullable=False,
            server_default="BOOKED",
        ),
        sa.Column("total_amount", sa.Integer(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=False, server_default=""),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.CheckConstraint("check_out > check_in", name="ck_reservations_dates"),
        sa.CheckConstraint("guests >= 1", name="ck_reservations_guests"),
    )
    op.create_index(
        "ix_reservations_room_dates", "reservations", ["room_id", "check_in", "check_out"]
    )
    op.create_index("ix_reservations_status", "reservations", ["status"])


def downgrade() -> None:
    op.drop_index("ix_reservations_status", table_name="reservations")
    op.drop_index("ix_reservations_room_dates", table_name="reservations")
    op.drop_table("reservations")

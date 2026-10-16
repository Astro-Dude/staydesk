import enum
from datetime import UTC, date, datetime

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


def utcnow() -> datetime:
    return datetime.now(UTC)


class RoomType(enum.StrEnum):
    SINGLE = "SINGLE"
    DOUBLE = "DOUBLE"
    DELUXE = "DELUXE"
    SUITE = "SUITE"


class Housekeeping(enum.StrEnum):
    CLEAN = "CLEAN"
    DIRTY = "DIRTY"
    OUT_OF_SERVICE = "OUT_OF_SERVICE"


class ReservationStatus(enum.StrEnum):
    BOOKED = "BOOKED"
    CHECKED_IN = "CHECKED_IN"
    CHECKED_OUT = "CHECKED_OUT"
    CANCELLED = "CANCELLED"


# Reservations in these states hold the room and block overlapping bookings.
ACTIVE_STATUSES = (ReservationStatus.BOOKED, ReservationStatus.CHECKED_IN)


def _enum(enum_cls: type[enum.Enum], name: str) -> Enum:
    # VARCHAR + CHECK constraint instead of a native PG enum: portable to SQLite for tests
    # and adding a value later doesn't need ALTER TYPE.
    return Enum(enum_cls, name=name, native_enum=False, create_constraint=True, length=20)


class Room(Base):
    __tablename__ = "rooms"
    __table_args__ = (
        CheckConstraint("capacity BETWEEN 1 AND 10", name="ck_rooms_capacity"),
        CheckConstraint("nightly_rate > 0", name="ck_rooms_nightly_rate"),
        CheckConstraint("floor >= 0", name="ck_rooms_floor"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    number: Mapped[str] = mapped_column(String(10), unique=True, nullable=False)
    room_type: Mapped[RoomType] = mapped_column(_enum(RoomType, "room_type"), nullable=False)
    floor: Mapped[int] = mapped_column(Integer, nullable=False)
    capacity: Mapped[int] = mapped_column(Integer, nullable=False)
    nightly_rate: Mapped[int] = mapped_column(Integer, nullable=False)
    housekeeping: Mapped[Housekeeping] = mapped_column(
        _enum(Housekeeping, "housekeeping"), nullable=False, default=Housekeeping.CLEAN
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )

    reservations: Mapped[list["Reservation"]] = relationship(
        back_populates="room", cascade="all, delete-orphan", passive_deletes=True
    )


class Reservation(Base):
    __tablename__ = "reservations"
    __table_args__ = (
        CheckConstraint("check_out > check_in", name="ck_reservations_dates"),
        CheckConstraint("guests >= 1", name="ck_reservations_guests"),
        Index("ix_reservations_room_dates", "room_id", "check_in", "check_out"),
        Index("ix_reservations_status", "status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    room_id: Mapped[int] = mapped_column(ForeignKey("rooms.id", ondelete="CASCADE"), nullable=False)
    guest_name: Mapped[str] = mapped_column(String(120), nullable=False)
    guest_email: Mapped[str] = mapped_column(String(255), nullable=False)
    guest_phone: Mapped[str] = mapped_column(String(30), nullable=False, default="")
    guests: Mapped[int] = mapped_column(Integer, nullable=False)
    check_in: Mapped[date] = mapped_column(Date, nullable=False)
    check_out: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[ReservationStatus] = mapped_column(
        _enum(ReservationStatus, "reservation_status"),
        nullable=False,
        default=ReservationStatus.BOOKED,
    )
    # Price is fixed when booked, so later rate changes don't rewrite existing bookings.
    total_amount: Mapped[int] = mapped_column(Integer, nullable=False)
    notes: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow
    )

    room: Mapped[Room] = relationship(back_populates="reservations", lazy="joined")

    @property
    def nights(self) -> int:
        return (self.check_out - self.check_in).days

    @property
    def room_number(self) -> str:
        return self.room.number

    @property
    def room_type(self) -> RoomType:
        return self.room.room_type

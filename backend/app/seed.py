"""Load demo rooms and reservations into an empty database.

Usage: python -m app.seed
Idempotent: does nothing if any room exists. On PostgreSQL a transaction-scoped advisory
lock stops several backend replicas from seeding at the same time.
"""

from datetime import date, timedelta

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from .db import SessionLocal
from .deps import get_today
from .models import Housekeeping, Reservation, ReservationStatus, Room, RoomType

SEED_LOCK_KEY = 7_820_001

ROOMS = [
    # number, type, floor, capacity, nightly rate (INR)
    ("101", RoomType.SINGLE, 1, 1, 2500),
    ("102", RoomType.SINGLE, 1, 1, 2500),
    ("103", RoomType.SINGLE, 1, 1, 2500),
    ("104", RoomType.DOUBLE, 1, 2, 3800),
    ("201", RoomType.DOUBLE, 2, 2, 4200),
    ("202", RoomType.DOUBLE, 2, 2, 4200),
    ("203", RoomType.DOUBLE, 2, 3, 4600),
    ("204", RoomType.DELUXE, 2, 3, 6500),
    ("301", RoomType.DELUXE, 3, 3, 6800),
    ("302", RoomType.DELUXE, 3, 3, 6800),
    ("401", RoomType.SUITE, 4, 4, 12000),
    ("402", RoomType.SUITE, 4, 5, 15500),
]

# guest, email, phone, room, guests, check-in offset, nights, status, notes
RESERVATIONS = [
    (
        "Aarav Mehta",
        "aarav.mehta@example.com",
        "+91 98200 11111",
        "201",
        2,
        -2,
        4,
        ReservationStatus.CHECKED_IN,
        "Late checkout requested",
    ),
    (
        "Diya Kapoor",
        "diya.kapoor@example.com",
        "+91 98200 22222",
        "401",
        3,
        -3,
        3,
        ReservationStatus.CHECKED_IN,
        "Anniversary - arrange flowers",
    ),
    (
        "Kabir Nair",
        "kabir.nair@example.com",
        "+91 98200 33333",
        "102",
        1,
        -1,
        3,
        ReservationStatus.CHECKED_IN,
        "",
    ),
    (
        "Ishita Rao",
        "ishita.rao@example.com",
        "+91 98200 44444",
        "204",
        2,
        0,
        2,
        ReservationStatus.BOOKED,
        "Airport pickup at 14:00",
    ),
    (
        "Rohan Iyer",
        "rohan.iyer@example.com",
        "+91 98200 55555",
        "101",
        1,
        0,
        1,
        ReservationStatus.BOOKED,
        "",
    ),
    (
        "Meera Joshi",
        "meera.joshi@example.com",
        "+91 98200 66666",
        "301",
        3,
        1,
        3,
        ReservationStatus.BOOKED,
        "Extra bed",
    ),
    (
        "Vivaan Gupta",
        "vivaan.gupta@example.com",
        "+91 98200 77777",
        "402",
        4,
        3,
        2,
        ReservationStatus.BOOKED,
        "Corporate booking",
    ),
    (
        "Anaya Singh",
        "anaya.singh@example.com",
        "+91 98200 88888",
        "202",
        2,
        5,
        4,
        ReservationStatus.BOOKED,
        "",
    ),
    (
        "Arjun Desai",
        "arjun.desai@example.com",
        "+91 98200 99999",
        "203",
        2,
        -3,
        3,
        ReservationStatus.CHECKED_OUT,
        "",
    ),
    (
        "Sara Thomas",
        "sara.thomas@example.com",
        "+91 98201 00000",
        "104",
        2,
        2,
        2,
        ReservationStatus.CANCELLED,
        "Flight cancelled",
    ),
]


def seed(db: Session, today: date) -> bool:
    """Insert demo data. Returns False when the database already had rooms."""
    if db.get_bind().dialect.name == "postgresql":
        db.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": SEED_LOCK_KEY})
    if db.scalar(select(func.count(Room.id))):
        db.rollback()
        return False

    rooms = {
        number: Room(number=number, room_type=kind, floor=floor, capacity=cap, nightly_rate=rate)
        for number, kind, floor, cap, rate in ROOMS
    }
    db.add_all(rooms.values())
    for name, email, phone, number, guests, offset, nights, state, notes in RESERVATIONS:
        room = rooms[number]
        check_in = today + timedelta(days=offset)
        db.add(
            Reservation(
                room=room,
                guest_name=name,
                guest_email=email,
                guest_phone=phone,
                guests=guests,
                check_in=check_in,
                check_out=check_in + timedelta(days=nights),
                status=state,
                total_amount=nights * room.nightly_rate,
                notes=notes,
            )
        )
    rooms["203"].housekeeping = Housekeeping.DIRTY  # guest checked out this morning
    rooms["302"].housekeeping = Housekeeping.OUT_OF_SERVICE  # AC repair
    db.commit()
    return True


if __name__ == "__main__":
    with SessionLocal() as session:
        created = seed(session, get_today())
    print("demo data loaded" if created else "database already has rooms; seed skipped")

from datetime import date
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..deps import DbSession, Today
from ..metrics import RESERVATION_EVENTS
from ..models import ACTIVE_STATUSES, Housekeeping, Reservation, ReservationStatus, Room
from ..schemas import ReservationCreate, ReservationOut, ReservationUpdate, validate_stay
from .rooms import get_room_or_404

router = APIRouter(prefix="/api/reservations", tags=["reservations"])


def get_reservation_or_404(db: Session, reservation_id: int) -> Reservation:
    reservation = db.get(Reservation, reservation_id)
    if reservation is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Reservation not found")
    return reservation


def ensure_bookable(
    db: Session,
    room: Room,
    guests: int,
    check_in: date,
    check_out: date,
    exclude_id: int | None = None,
) -> None:
    if room.housekeeping == Housekeeping.OUT_OF_SERVICE:
        raise HTTPException(status.HTTP_409_CONFLICT, f"Room {room.number} is out of service")
    if guests > room.capacity:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            f"Room {room.number} holds at most {room.capacity} guest(s)",
        )
    # Two stays overlap when each starts before the other ends. Check-out day is free
    # for the next guest, hence the strict comparisons.
    clash = select(Reservation.id).where(
        Reservation.room_id == room.id,
        Reservation.status.in_(ACTIVE_STATUSES),
        Reservation.check_in < check_out,
        Reservation.check_out > check_in,
    )
    if exclude_id is not None:
        clash = clash.where(Reservation.id != exclude_id)
    if db.scalar(clash.limit(1)) is not None:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"Room {room.number} is already booked between {check_in} and {check_out}",
        )


def ensure_not_in_past(check_in: date, today: date) -> None:
    if check_in < today:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "check_in cannot be in the past")


def ensure_status(reservation: Reservation, expected: ReservationStatus, action: str) -> None:
    if reservation.status != expected:
        label = reservation.status.value.replace("_", " ").lower()
        raise HTTPException(status.HTTP_409_CONFLICT, f"Cannot {action} a {label} reservation")


@router.get("", response_model=list[ReservationOut])
def list_reservations(
    db: DbSession,
    status_filter: Annotated[ReservationStatus | None, Query(alias="status")] = None,
    room_id: int | None = None,
):
    query = select(Reservation).order_by(Reservation.check_in.desc(), Reservation.id.desc())
    if status_filter is not None:
        query = query.where(Reservation.status == status_filter)
    if room_id is not None:
        query = query.where(Reservation.room_id == room_id)
    return list(db.scalars(query))


@router.get("/{reservation_id}", response_model=ReservationOut)
def get_reservation(reservation_id: int, db: DbSession):
    return get_reservation_or_404(db, reservation_id)


@router.post("", response_model=ReservationOut, status_code=status.HTTP_201_CREATED)
def create_reservation(payload: ReservationCreate, db: DbSession, today: Today):
    room = get_room_or_404(db, payload.room_id)
    ensure_not_in_past(payload.check_in, today)
    ensure_bookable(db, room, payload.guests, payload.check_in, payload.check_out)
    reservation = Reservation(
        **payload.model_dump(),
        total_amount=(payload.check_out - payload.check_in).days * room.nightly_rate,
    )
    db.add(reservation)
    db.commit()
    db.refresh(reservation)
    RESERVATION_EVENTS.labels(event="created").inc()
    return reservation


@router.put("/{reservation_id}", response_model=ReservationOut)
def update_reservation(
    reservation_id: int, payload: ReservationUpdate, db: DbSession, today: Today
):
    reservation = get_reservation_or_404(db, reservation_id)
    ensure_status(reservation, ReservationStatus.BOOKED, "edit")
    changes = payload.model_dump(exclude_unset=True, exclude_none=True)

    room = get_room_or_404(db, changes.get("room_id", reservation.room_id))
    check_in = changes.get("check_in", reservation.check_in)
    check_out = changes.get("check_out", reservation.check_out)
    guests = changes.get("guests", reservation.guests)
    try:
        validate_stay(check_in, check_out)
    except ValueError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc)) from exc
    if check_in != reservation.check_in:
        ensure_not_in_past(check_in, today)
    ensure_bookable(db, room, guests, check_in, check_out, exclude_id=reservation.id)

    repriced = {"room_id", "check_in", "check_out"} & changes.keys()
    for field, value in changes.items():
        setattr(reservation, field, value)
    if repriced:
        reservation.room = room
        reservation.total_amount = (check_out - check_in).days * room.nightly_rate
    db.commit()
    db.refresh(reservation)
    return reservation


@router.delete("/{reservation_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_reservation(reservation_id: int, db: DbSession):
    reservation = get_reservation_or_404(db, reservation_id)
    if reservation.status == ReservationStatus.CHECKED_IN:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "Guest is currently checked in; check them out first"
        )
    db.delete(reservation)
    db.commit()


@router.post("/{reservation_id}/check-in", response_model=ReservationOut)
def check_in_reservation(reservation_id: int, db: DbSession, today: Today):
    reservation = get_reservation_or_404(db, reservation_id)
    ensure_status(reservation, ReservationStatus.BOOKED, "check in")
    if today < reservation.check_in:
        raise HTTPException(
            status.HTTP_409_CONFLICT, f"Check-in opens on {reservation.check_in.isoformat()}"
        )
    if today >= reservation.check_out:
        raise HTTPException(status.HTTP_409_CONFLICT, "This stay has already ended")
    room = reservation.room
    if room.housekeeping != Housekeeping.CLEAN:
        state = room.housekeeping.value.replace("_", " ").lower()
        raise HTTPException(status.HTTP_409_CONFLICT, f"Room {room.number} is not ready ({state})")
    still_occupied = db.scalar(
        select(Reservation.id).where(
            Reservation.room_id == room.id,
            Reservation.status == ReservationStatus.CHECKED_IN,
        )
    )
    if still_occupied is not None:
        raise HTTPException(
            status.HTTP_409_CONFLICT, f"Room {room.number} is still occupied by another guest"
        )
    reservation.status = ReservationStatus.CHECKED_IN
    db.commit()
    db.refresh(reservation)
    RESERVATION_EVENTS.labels(event="checked_in").inc()
    return reservation


@router.post("/{reservation_id}/check-out", response_model=ReservationOut)
def check_out_reservation(reservation_id: int, db: DbSession):
    reservation = get_reservation_or_404(db, reservation_id)
    ensure_status(reservation, ReservationStatus.CHECKED_IN, "check out")
    reservation.status = ReservationStatus.CHECKED_OUT
    reservation.room.housekeeping = Housekeeping.DIRTY
    db.commit()
    db.refresh(reservation)
    RESERVATION_EVENTS.labels(event="checked_out").inc()
    return reservation


@router.post("/{reservation_id}/cancel", response_model=ReservationOut)
def cancel_reservation(reservation_id: int, db: DbSession):
    reservation = get_reservation_or_404(db, reservation_id)
    ensure_status(reservation, ReservationStatus.BOOKED, "cancel")
    reservation.status = ReservationStatus.CANCELLED
    db.commit()
    db.refresh(reservation)
    RESERVATION_EVENTS.labels(event="cancelled").inc()
    return reservation

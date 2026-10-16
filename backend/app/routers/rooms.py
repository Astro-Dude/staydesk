from datetime import date
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import exists, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..deps import DbSession
from ..models import ACTIVE_STATUSES, Housekeeping, Reservation, ReservationStatus, Room, RoomType
from ..schemas import RoomCreate, RoomOut, RoomUpdate

router = APIRouter(prefix="/api/rooms", tags=["rooms"])


def occupied_room_ids(db: Session) -> set[int]:
    query = select(Reservation.room_id).where(Reservation.status == ReservationStatus.CHECKED_IN)
    return set(db.scalars(query))


def to_room_out(room: Room, occupied_ids: set[int]) -> RoomOut:
    return RoomOut.model_validate(room).model_copy(update={"occupied": room.id in occupied_ids})


def get_room_or_404(db: Session, room_id: int) -> Room:
    room = db.get(Room, room_id)
    if room is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Room not found")
    return room


def ensure_number_free(db: Session, number: str, exclude_id: int | None = None) -> None:
    query = select(Room.id).where(Room.number == number)
    if exclude_id is not None:
        query = query.where(Room.id != exclude_id)
    if db.scalar(query) is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, f"Room {number} already exists")


@router.get("", response_model=list[RoomOut])
def list_rooms(
    db: DbSession,
    room_type: RoomType | None = None,
    housekeeping: Housekeeping | None = None,
):
    query = select(Room).order_by(Room.floor, Room.number)
    if room_type is not None:
        query = query.where(Room.room_type == room_type)
    if housekeeping is not None:
        query = query.where(Room.housekeeping == housekeeping)
    occupied = occupied_room_ids(db)
    return [to_room_out(room, occupied) for room in db.scalars(query)]


@router.get("/availability", response_model=list[RoomOut])
def room_availability(
    db: DbSession,
    check_in: date,
    check_out: date,
    guests: Annotated[int, Query(ge=1, le=10)] = 1,
):
    """Rooms that can take a new booking for the given stay."""
    if check_out <= check_in:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, "check_out must be after check_in"
        )
    clash = exists().where(
        Reservation.room_id == Room.id,
        Reservation.status.in_(ACTIVE_STATUSES),
        Reservation.check_in < check_out,
        Reservation.check_out > check_in,
    )
    query = (
        select(Room)
        .where(Room.housekeeping != Housekeeping.OUT_OF_SERVICE, Room.capacity >= guests, ~clash)
        .order_by(Room.nightly_rate, Room.number)
    )
    occupied = occupied_room_ids(db)
    return [to_room_out(room, occupied) for room in db.scalars(query)]


@router.get("/{room_id}", response_model=RoomOut)
def get_room(room_id: int, db: DbSession):
    return to_room_out(get_room_or_404(db, room_id), occupied_room_ids(db))


@router.post("", response_model=RoomOut, status_code=status.HTTP_201_CREATED)
def create_room(payload: RoomCreate, db: DbSession):
    ensure_number_free(db, payload.number)
    room = Room(**payload.model_dump())
    db.add(room)
    try:
        db.commit()
    except IntegrityError as exc:  # lost a race with a concurrent insert of the same number
        db.rollback()
        raise HTTPException(
            status.HTTP_409_CONFLICT, f"Room {payload.number} already exists"
        ) from exc
    db.refresh(room)
    return to_room_out(room, set())


@router.put("/{room_id}", response_model=RoomOut)
def update_room(room_id: int, payload: RoomUpdate, db: DbSession):
    room = get_room_or_404(db, room_id)
    changes = payload.model_dump(exclude_unset=True, exclude_none=True)
    if "number" in changes:
        ensure_number_free(db, changes["number"], exclude_id=room.id)
    for field, value in changes.items():
        setattr(room, field, value)
    db.commit()
    db.refresh(room)
    return to_room_out(room, occupied_room_ids(db))


@router.delete("/{room_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_room(room_id: int, db: DbSession):
    room = get_room_or_404(db, room_id)
    has_active = db.scalar(
        select(Reservation.id)
        .where(Reservation.room_id == room.id, Reservation.status.in_(ACTIVE_STATUSES))
        .limit(1)
    )
    if has_active is not None:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"Room {room.number} has upcoming or in-house reservations; cancel them first",
        )
    db.delete(room)
    db.commit()

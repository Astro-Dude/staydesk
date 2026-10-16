from datetime import date, timedelta

from fastapi import APIRouter
from sqlalchemy import distinct, func, select

from ..deps import DbSession, Today
from ..models import Housekeeping, Reservation, ReservationStatus, Room
from ..schemas import DashboardStats, TodayBoard

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


def month_bounds(day: date) -> tuple[date, date]:
    """First day of `day`'s month and first day of the following month."""
    start = day.replace(day=1)
    return start, (start + timedelta(days=32)).replace(day=1)


@router.get("/stats", response_model=DashboardStats)
def dashboard_stats(db: DbSession, today: Today):
    def count(query) -> int:
        return db.scalar(query) or 0

    total_rooms = count(select(func.count(Room.id)))
    out_of_service = count(
        select(func.count(Room.id)).where(Room.housekeeping == Housekeeping.OUT_OF_SERVICE)
    )
    rooms_to_clean = count(
        select(func.count(Room.id)).where(Room.housekeeping == Housekeeping.DIRTY)
    )
    occupied = count(
        select(func.count(distinct(Reservation.room_id))).where(
            Reservation.status == ReservationStatus.CHECKED_IN
        )
    )
    sellable = total_rooms - out_of_service
    month_start, next_month = month_bounds(today)

    return DashboardStats(
        total_rooms=total_rooms,
        occupied_rooms=occupied,
        available_rooms=max(sellable - occupied, 0),
        out_of_service_rooms=out_of_service,
        rooms_to_clean=rooms_to_clean,
        occupancy_rate=round(occupied / sellable * 100, 1) if sellable else 0.0,
        arrivals_today=count(
            select(func.count(Reservation.id)).where(
                Reservation.status == ReservationStatus.BOOKED, Reservation.check_in == today
            )
        ),
        departures_today=count(
            select(func.count(Reservation.id)).where(
                Reservation.status == ReservationStatus.CHECKED_IN,
                Reservation.check_out <= today,
            )
        ),
        in_house_guests=count(
            select(func.sum(Reservation.guests)).where(
                Reservation.status == ReservationStatus.CHECKED_IN
            )
        ),
        upcoming_reservations=count(
            select(func.count(Reservation.id)).where(
                Reservation.status == ReservationStatus.BOOKED, Reservation.check_in > today
            )
        ),
        revenue_this_month=count(
            select(func.sum(Reservation.total_amount)).where(
                Reservation.status != ReservationStatus.CANCELLED,
                Reservation.check_in >= month_start,
                Reservation.check_in < next_month,
            )
        ),
    )


@router.get("/today", response_model=TodayBoard)
def today_board(db: DbSession, today: Today):
    """Front-desk worklist: who arrives today and who is due (or overdue) to leave."""
    arrivals = db.scalars(
        select(Reservation)
        .where(Reservation.status == ReservationStatus.BOOKED, Reservation.check_in == today)
        .order_by(Reservation.id)
    )
    departures = db.scalars(
        select(Reservation)
        .where(Reservation.status == ReservationStatus.CHECKED_IN, Reservation.check_out <= today)
        .order_by(Reservation.check_out, Reservation.id)
    )
    return TodayBoard(arrivals=list(arrivals), departures=list(departures))

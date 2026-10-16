from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator

from .models import Housekeeping, ReservationStatus, RoomType

MAX_STAY_NIGHTS = 30


# ---------- Rooms ----------


class RoomBase(BaseModel):
    number: str = Field(min_length=1, max_length=10, pattern=r"^[A-Za-z0-9-]+$", examples=["204"])
    room_type: RoomType
    floor: int = Field(ge=0, le=200)
    capacity: int = Field(ge=1, le=10)
    nightly_rate: int = Field(gt=0, le=1_000_000, description="Price per night in INR")


class RoomCreate(RoomBase):
    housekeeping: Housekeeping = Housekeeping.CLEAN


class RoomUpdate(BaseModel):
    number: str | None = Field(
        default=None, min_length=1, max_length=10, pattern=r"^[A-Za-z0-9-]+$"
    )
    room_type: RoomType | None = None
    floor: int | None = Field(default=None, ge=0, le=200)
    capacity: int | None = Field(default=None, ge=1, le=10)
    nightly_rate: int | None = Field(default=None, gt=0, le=1_000_000)
    housekeeping: Housekeeping | None = None


class RoomOut(RoomCreate):
    id: int
    occupied: bool = False
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ---------- Reservations ----------


def validate_stay(check_in: date, check_out: date) -> None:
    if check_out <= check_in:
        raise ValueError("check_out must be after check_in")
    if (check_out - check_in).days > MAX_STAY_NIGHTS:
        raise ValueError(f"stays longer than {MAX_STAY_NIGHTS} nights are not supported")


class ReservationCreate(BaseModel):
    room_id: int
    guest_name: str = Field(min_length=2, max_length=120)
    guest_email: EmailStr
    guest_phone: str = Field(default="", max_length=30)
    guests: int = Field(ge=1, le=10)
    check_in: date
    check_out: date
    notes: str = Field(default="", max_length=1000)

    @model_validator(mode="after")
    def check_dates(self) -> "ReservationCreate":
        validate_stay(self.check_in, self.check_out)
        return self


class ReservationUpdate(BaseModel):
    room_id: int | None = None
    guest_name: str | None = Field(default=None, min_length=2, max_length=120)
    guest_email: EmailStr | None = None
    guest_phone: str | None = Field(default=None, max_length=30)
    guests: int | None = Field(default=None, ge=1, le=10)
    check_in: date | None = None
    check_out: date | None = None
    notes: str | None = Field(default=None, max_length=1000)


class ReservationOut(BaseModel):
    id: int
    room_id: int
    room_number: str
    room_type: RoomType
    guest_name: str
    guest_email: str
    guest_phone: str
    guests: int
    check_in: date
    check_out: date
    nights: int
    total_amount: int
    status: ReservationStatus
    notes: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ---------- Dashboard ----------


class DashboardStats(BaseModel):
    total_rooms: int
    occupied_rooms: int
    available_rooms: int
    out_of_service_rooms: int
    rooms_to_clean: int
    occupancy_rate: float = Field(description="Occupied share of sellable rooms, 0-100")
    arrivals_today: int
    departures_today: int
    in_house_guests: int
    upcoming_reservations: int
    revenue_this_month: int = Field(description="Booked (non-cancelled) revenue in INR")


class TodayBoard(BaseModel):
    arrivals: list[ReservationOut]
    departures: list[ReservationOut]

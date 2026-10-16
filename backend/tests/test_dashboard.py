from datetime import date

from app.routers.dashboard import month_bounds
from app.seed import seed

from helpers import TODAY, day


def test_stats_on_empty_hotel(client):
    stats = client.get("/api/dashboard/stats").json()
    assert stats["total_rooms"] == 0
    assert stats["occupancy_rate"] == 0.0
    assert stats["revenue_this_month"] == 0


def test_stats_reflect_front_desk_activity(client, make_room, make_reservation):
    rooms = [make_room(nightly_rate=1000) for _ in range(4)]
    make_room(housekeeping="OUT_OF_SERVICE")

    in_house = make_reservation(room=rooms[0], guests=2, check_in=day(0), check_out=day(2))
    client.post(f"/api/reservations/{in_house['id']}/check-in")
    make_reservation(room=rooms[1], check_in=day(0), check_out=day(1))  # arriving today
    make_reservation(room=rooms[2], check_in=day(3), check_out=day(5))  # upcoming
    cancelled = make_reservation(room=rooms[3], check_in=day(1), check_out=day(2))
    client.post(f"/api/reservations/{cancelled['id']}/cancel")

    stats = client.get("/api/dashboard/stats").json()
    assert stats["total_rooms"] == 5
    assert stats["out_of_service_rooms"] == 1
    assert stats["occupied_rooms"] == 1
    assert stats["available_rooms"] == 3
    assert stats["occupancy_rate"] == 25.0  # 1 of 4 sellable rooms
    assert stats["arrivals_today"] == 1
    assert stats["departures_today"] == 0
    assert stats["in_house_guests"] == 2
    assert stats["upcoming_reservations"] == 1
    assert stats["revenue_this_month"] == 2000 + 1000 + 2000  # cancelled one excluded


def test_today_board_lists_arrivals_and_departures(client, session_factory):
    with session_factory() as db:
        assert seed(db, TODAY) is True

    board = client.get("/api/dashboard/today").json()
    arrivals = {r["guest_name"] for r in board["arrivals"]}
    departures = {r["guest_name"] for r in board["departures"]}
    assert arrivals == {"Ishita Rao", "Rohan Iyer"}
    assert departures == {"Diya Kapoor"}


def test_seed_is_idempotent(client, session_factory):
    with session_factory() as db:
        assert seed(db, TODAY) is True
    with session_factory() as db:
        assert seed(db, TODAY) is False
    assert len(client.get("/api/rooms").json()) == 12


def test_month_bounds_handles_year_end():
    assert month_bounds(date(2026, 12, 31)) == (date(2026, 12, 1), date(2027, 1, 1))
    assert month_bounds(date(2026, 2, 14)) == (date(2026, 2, 1), date(2026, 3, 1))

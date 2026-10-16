import pytest

from helpers import day


def test_create_reservation_prices_the_stay(client, make_room):
    room = make_room(number="204", nightly_rate=6500, capacity=3)
    response = client.post(
        "/api/reservations",
        json={
            "room_id": room["id"],
            "guest_name": "Ishita Rao",
            "guest_email": "ishita@example.com",
            "guests": 2,
            "check_in": day(1),
            "check_out": day(4),
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "BOOKED"
    assert body["nights"] == 3
    assert body["total_amount"] == 3 * 6500
    assert body["room_number"] == "204"
    assert body["room_type"] == "DOUBLE"


@pytest.mark.parametrize(
    ("check_in", "check_out", "message"),
    [
        (day(3), day(3), "check_out must be after check_in"),
        (day(3), day(1), "check_out must be after check_in"),
        (day(0), day(31), "longer than 30 nights"),
    ],
)
def test_create_reservation_rejects_bad_dates(client, make_room, check_in, check_out, message):
    room = make_room()
    response = client.post(
        "/api/reservations",
        json={
            "room_id": room["id"],
            "guest_name": "Test Guest",
            "guest_email": "guest@example.com",
            "guests": 1,
            "check_in": check_in,
            "check_out": check_out,
        },
    )
    assert response.status_code == 422
    assert message in response.text


def test_create_reservation_rejects_past_check_in(client, make_room):
    room = make_room()
    response = client.post(
        "/api/reservations",
        json={
            "room_id": room["id"],
            "guest_name": "Late Guest",
            "guest_email": "late@example.com",
            "guests": 1,
            "check_in": day(-1),
            "check_out": day(2),
        },
    )
    assert response.status_code == 422
    assert response.json()["detail"] == "check_in cannot be in the past"


def test_create_reservation_rejects_invalid_email(client, make_room):
    room = make_room()
    response = client.post(
        "/api/reservations",
        json={
            "room_id": room["id"],
            "guest_name": "No Mail",
            "guest_email": "not-an-email",
            "guests": 1,
            "check_in": day(0),
            "check_out": day(1),
        },
    )
    assert response.status_code == 422


def test_create_reservation_for_unknown_room(client):
    response = client.post(
        "/api/reservations",
        json={
            "room_id": 404,
            "guest_name": "Lost Guest",
            "guest_email": "lost@example.com",
            "guests": 1,
            "check_in": day(0),
            "check_out": day(1),
        },
    )
    assert response.status_code == 404


def test_create_reservation_over_capacity(client, make_room, make_reservation):
    room = make_room(capacity=2)
    response = client.post(
        "/api/reservations",
        json={
            "room_id": room["id"],
            "guest_name": "Big Family",
            "guest_email": "family@example.com",
            "guests": 4,
            "check_in": day(0),
            "check_out": day(2),
        },
    )
    assert response.status_code == 422
    assert "at most 2" in response.json()["detail"]


def test_overlapping_booking_is_rejected(client, make_room, make_reservation):
    room = make_room()
    make_reservation(room=room, check_in=day(2), check_out=day(5))
    response = client.post(
        "/api/reservations",
        json={
            "room_id": room["id"],
            "guest_name": "Second Guest",
            "guest_email": "two@example.com",
            "guests": 1,
            "check_in": day(4),
            "check_out": day(6),
        },
    )
    assert response.status_code == 409
    assert "already booked" in response.json()["detail"]


def test_back_to_back_bookings_are_allowed(make_room, make_reservation):
    room = make_room()
    make_reservation(room=room, check_in=day(2), check_out=day(5))
    # The next guest can arrive on the day the previous one leaves.
    make_reservation(room=room, check_in=day(5), check_out=day(7))


def test_cancelled_booking_frees_the_room(client, make_room, make_reservation):
    room = make_room()
    first = make_reservation(room=room, check_in=day(1), check_out=day(3))
    client.post(f"/api/reservations/{first['id']}/cancel")
    make_reservation(room=room, check_in=day(1), check_out=day(3))


def test_out_of_service_room_cannot_be_booked(client, make_room):
    room = make_room(housekeeping="OUT_OF_SERVICE")
    response = client.post(
        "/api/reservations",
        json={
            "room_id": room["id"],
            "guest_name": "Test Guest",
            "guest_email": "guest@example.com",
            "guests": 1,
            "check_in": day(0),
            "check_out": day(1),
        },
    )
    assert response.status_code == 409


def test_list_and_filter_reservations(client, make_reservation):
    first = make_reservation(check_in=day(1), check_out=day(2))
    second = make_reservation(check_in=day(5), check_out=day(6))
    client.post(f"/api/reservations/{first['id']}/cancel")

    all_ids = [r["id"] for r in client.get("/api/reservations").json()]
    assert all_ids == [second["id"], first["id"]]  # latest check-in first

    cancelled = client.get("/api/reservations", params={"status": "CANCELLED"}).json()
    assert [r["id"] for r in cancelled] == [first["id"]]

    by_room = client.get("/api/reservations", params={"room_id": second["room_id"]}).json()
    assert [r["id"] for r in by_room] == [second["id"]]


def test_get_reservation_not_found(client):
    assert client.get("/api/reservations/12345").status_code == 404


def test_update_reservation_reprices_new_dates(client, make_room, make_reservation):
    room = make_room(nightly_rate=3000)
    reservation = make_reservation(room=room, check_in=day(1), check_out=day(3))
    response = client.put(
        f"/api/reservations/{reservation['id']}",
        json={"check_out": day(6), "notes": "Extended stay"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["nights"] == 5
    assert body["total_amount"] == 5 * 3000
    assert body["notes"] == "Extended stay"


def test_update_reservation_can_move_rooms(client, make_room, make_reservation):
    reservation = make_reservation(check_in=day(1), check_out=day(3))
    suite = make_room(number="401", room_type="SUITE", nightly_rate=12000, capacity=4)
    response = client.put(f"/api/reservations/{reservation['id']}", json={"room_id": suite["id"]})
    assert response.status_code == 200
    assert response.json()["room_number"] == "401"
    assert response.json()["total_amount"] == 2 * 12000


def test_update_reservation_validates_merged_dates(client, make_reservation):
    reservation = make_reservation(check_in=day(2), check_out=day(4))
    response = client.put(f"/api/reservations/{reservation['id']}", json={"check_out": day(1)})
    assert response.status_code == 422


def test_update_reservation_detects_overlap(client, make_room, make_reservation):
    room = make_room()
    make_reservation(room=room, check_in=day(5), check_out=day(8))
    mine = make_reservation(room=room, check_in=day(1), check_out=day(3))
    response = client.put(f"/api/reservations/{mine['id']}", json={"check_out": day(6)})
    assert response.status_code == 409


def test_only_booked_reservations_can_be_edited(client, make_reservation):
    reservation = make_reservation()
    client.post(f"/api/reservations/{reservation['id']}/check-in")
    response = client.put(f"/api/reservations/{reservation['id']}", json={"guests": 1})
    assert response.status_code == 409


def test_full_stay_lifecycle(client, make_reservation):
    reservation = make_reservation(check_in=day(0), check_out=day(2))
    rid, room_id = reservation["id"], reservation["room_id"]

    checked_in = client.post(f"/api/reservations/{rid}/check-in")
    assert checked_in.status_code == 200
    assert checked_in.json()["status"] == "CHECKED_IN"
    assert client.get(f"/api/rooms/{room_id}").json()["occupied"] is True

    checked_out = client.post(f"/api/reservations/{rid}/check-out")
    assert checked_out.status_code == 200
    assert checked_out.json()["status"] == "CHECKED_OUT"
    room = client.get(f"/api/rooms/{room_id}").json()
    assert room["occupied"] is False
    assert room["housekeeping"] == "DIRTY"  # housekeeping must turn the room around


def test_check_in_before_arrival_date_is_rejected(client, make_reservation):
    reservation = make_reservation(check_in=day(2), check_out=day(4))
    response = client.post(f"/api/reservations/{reservation['id']}/check-in")
    assert response.status_code == 409
    assert "opens on" in response.json()["detail"]


def test_check_in_requires_clean_room(client, make_room, make_reservation):
    room = make_room(housekeeping="DIRTY")
    reservation = make_reservation(room=room)
    response = client.post(f"/api/reservations/{reservation['id']}/check-in")
    assert response.status_code == 409
    assert "not ready" in response.json()["detail"]


def test_invalid_status_transitions(client, make_reservation):
    reservation = make_reservation()
    rid = reservation["id"]
    assert client.post(f"/api/reservations/{rid}/check-out").status_code == 409
    client.post(f"/api/reservations/{rid}/cancel")
    assert client.post(f"/api/reservations/{rid}/check-in").status_code == 409
    assert client.post(f"/api/reservations/{rid}/cancel").status_code == 409


def test_delete_reservation(client, make_reservation):
    reservation = make_reservation()
    assert client.delete(f"/api/reservations/{reservation['id']}").status_code == 204
    assert client.get(f"/api/reservations/{reservation['id']}").status_code == 404


def test_delete_checked_in_reservation_is_blocked(client, make_reservation):
    reservation = make_reservation()
    client.post(f"/api/reservations/{reservation['id']}/check-in")
    assert client.delete(f"/api/reservations/{reservation['id']}").status_code == 409

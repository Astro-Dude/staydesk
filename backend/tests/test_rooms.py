from helpers import day


def test_create_room(client):
    payload = {
        "number": "301",
        "room_type": "SUITE",
        "floor": 3,
        "capacity": 4,
        "nightly_rate": 12000,
    }
    response = client.post("/api/rooms", json=payload)
    assert response.status_code == 201
    body = response.json()
    assert body["number"] == "301"
    assert body["housekeeping"] == "CLEAN"
    assert body["occupied"] is False


def test_create_room_rejects_duplicate_number(client, make_room):
    make_room(number="101")
    response = client.post(
        "/api/rooms",
        json={
            "number": "101",
            "room_type": "SINGLE",
            "floor": 1,
            "capacity": 1,
            "nightly_rate": 2500,
        },
    )
    assert response.status_code == 409
    assert "already exists" in response.json()["detail"]


def test_create_room_validates_payload(client):
    response = client.post(
        "/api/rooms",
        json={
            "number": "1 01",
            "room_type": "PENTHOUSE",
            "floor": -1,
            "capacity": 0,
            "nightly_rate": 0,
        },
    )
    assert response.status_code == 422
    invalid_fields = {error["loc"][-1] for error in response.json()["detail"]}
    assert invalid_fields == {"number", "room_type", "floor", "capacity", "nightly_rate"}


def test_list_rooms_sorted_and_filtered(client, make_room):
    make_room(number="201", floor=2, room_type="DELUXE")
    make_room(number="101", floor=1, room_type="SINGLE", capacity=1)
    make_room(number="102", floor=1, room_type="SINGLE", capacity=1, housekeeping="DIRTY")

    numbers = [room["number"] for room in client.get("/api/rooms").json()]
    assert numbers == ["101", "102", "201"]

    singles = client.get("/api/rooms", params={"room_type": "SINGLE"}).json()
    assert {room["number"] for room in singles} == {"101", "102"}

    dirty = client.get("/api/rooms", params={"housekeeping": "DIRTY"}).json()
    assert [room["number"] for room in dirty] == ["102"]


def test_get_room_not_found(client):
    response = client.get("/api/rooms/999")
    assert response.status_code == 404
    assert response.json() == {"detail": "Room not found"}


def test_update_room(client, make_room):
    room = make_room()
    response = client.put(
        f"/api/rooms/{room['id']}", json={"housekeeping": "OUT_OF_SERVICE", "nightly_rate": 4500}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["housekeeping"] == "OUT_OF_SERVICE"
    assert body["nightly_rate"] == 4500
    assert body["number"] == room["number"]


def test_update_room_cannot_take_existing_number(client, make_room):
    make_room(number="101")
    other = make_room(number="102")
    response = client.put(f"/api/rooms/{other['id']}", json={"number": "101"})
    assert response.status_code == 409


def test_delete_room(client, make_room):
    room = make_room()
    assert client.delete(f"/api/rooms/{room['id']}").status_code == 204
    assert client.get(f"/api/rooms/{room['id']}").status_code == 404


def test_delete_room_with_active_reservation_is_blocked(client, make_reservation):
    reservation = make_reservation()
    response = client.delete(f"/api/rooms/{reservation['room_id']}")
    assert response.status_code == 409


def test_delete_room_removes_past_reservations(client, make_reservation):
    reservation = make_reservation()
    client.post(f"/api/reservations/{reservation['id']}/cancel")
    assert client.delete(f"/api/rooms/{reservation['room_id']}").status_code == 204
    assert client.get(f"/api/reservations/{reservation['id']}").status_code == 404


def test_availability_excludes_booked_full_and_out_of_service_rooms(
    client, make_room, make_reservation
):
    booked = make_room(number="101")
    small = make_room(number="102", capacity=1)
    broken = make_room(number="103", housekeeping="OUT_OF_SERVICE")
    free = make_room(number="104")
    make_reservation(room=booked, check_in=day(1), check_out=day(4))

    response = client.get(
        "/api/rooms/availability", params={"check_in": day(2), "check_out": day(5), "guests": 2}
    )
    assert response.status_code == 200
    available = {room["id"] for room in response.json()}
    assert free["id"] in available
    assert not available & {booked["id"], small["id"], broken["id"]}


def test_availability_rejects_inverted_dates(client):
    response = client.get(
        "/api/rooms/availability", params={"check_in": day(3), "check_out": day(1)}
    )
    assert response.status_code == 422

def test_turn_timer_seconds_flows_from_create_request_into_ruleset(client):
    data = client.post("/api/games", json={"host_name": "Alice", "turn_timer_seconds": 90}).json()
    assert data["game"]["ruleset"]["turn_timer_seconds"] == 90


def test_turn_timer_defaults_to_off(client):
    data = client.post("/api/games", json={"host_name": "Alice"}).json()
    assert data["game"]["ruleset"]["turn_timer_seconds"] == 0
    assert data["game"]["turn_started_at"] is None


def test_turn_started_at_is_timezone_aware_on_the_wire(client):
    # Regression: SQLite has no real tz-aware storage type, so a
    # DateTime(timezone=True) column round-trips as a *naive* Python
    # datetime even though it was written as UTC — serializing that naive
    # value straight to JSON drops the offset, and a browser's `new
    # Date(...)` then parses an offset-less ISO string as *local* time, not
    # UTC. That silently broke the turn-timer countdown (deadline math came
    # out hours off depending on the host machine's timezone) without ever
    # touching a status code or throwing anywhere server-side. Every
    # datetime field must round-trip through schemas.UtcDatetime — this
    # locks in the wire format so a future field that forgets to can't
    # regress silently.
    data = client.post("/api/games", json={"host_name": "Alice"}).json()
    code = data["game"]["code"]
    host_token = data["host_token"]
    host_id = data["host_player_id"]
    bob = client.post(f"/api/games/{code}/join", json={"name": "Bob"}).json()
    client.post(f"/api/games/{code}/start", headers={"x-host-token": host_token})

    client.post(f"/api/games/{code}/roll_for_order", json={"player_id": host_id, "roll": 5}, headers={"x-host-token": host_token})
    r = client.post(f"/api/games/{code}/roll_for_order", json={"player_id": bob["player_id"], "roll": 2}, headers={"x-host-token": host_token})

    turn_started_at = r.json()["game"]["turn_started_at"]
    assert turn_started_at is not None
    assert turn_started_at.endswith("Z") or turn_started_at[-6] in "+-"

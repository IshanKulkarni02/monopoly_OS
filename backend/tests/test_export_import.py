def _setup_game(client):
    data = client.post("/api/games", json={"host_name": "Alice", "play_mode": "virtual"}).json()
    code = data["game"]["code"]
    host_id = data["host_player_id"]
    host_token = data["player_token"]
    bob = client.post(f"/api/games/{code}/join", json={"name": "Bob"}).json()
    client.post(f"/api/games/{code}/start", headers={"x-host-token": data["host_token"]})
    return code, data["host_token"], host_id, host_token, bob["player_id"], bob["player_token"]


def test_export_requires_host_token(client):
    code, host_token, *_ = _setup_game(client)
    r = client.get(f"/api/games/{code}/export")
    assert r.status_code == 403


def test_export_then_import_round_trips_playable_state(client):
    code, host_token, host_id, host_player_token, bob_id, bob_token = _setup_game(client)
    state = client.get(f"/api/games/{code}").json()
    prop = next(p for p in state["properties"] if p["price"] > 0)
    client.post(f"/api/games/{code}/properties/{prop['id']}/purchase", headers={"x-player-id": host_id, "x-player-token": host_player_token})

    exported = client.get(f"/api/games/{code}/export", headers={"x-host-token": host_token}).json()
    assert exported["version"] == 1
    assert len(exported["players"]) == 2

    r = client.post("/api/games/import", json={"data": exported})
    assert r.status_code == 200, r.text
    imported = r.json()
    new_code = imported["game"]["code"]
    assert new_code != code  # fresh game, fresh code
    assert imported["host_token"] != host_token  # fresh tokens, not the original game's

    new_state = imported["game"]
    assert new_state["status"] == "active"  # resumes directly, skips the lobby
    assert len(new_state["players"]) == 2
    assert {p["name"] for p in new_state["players"]} == {"Alice", "Bob"}

    new_alice = next(p for p in new_state["players"] if p["name"] == "Alice")
    old_alice = next(p for p in state["players"] if p["id"] == host_id)
    assert new_alice["balance"] == old_alice["balance"] - prop["price"]
    assert new_alice["is_host"] is True

    new_prop = next(p for p in new_state["properties"] if p["space_index"] == prop["space_index"])
    assert new_prop["owner_id"] == new_alice["id"]


def test_import_rejects_unknown_board_key(client):
    r = client.post("/api/games/import", json={"data": {"version": 1, "board_key": "no-such-board", "players": [{"name": "X"}]}})
    assert r.status_code == 400


def test_import_rejects_wrong_version(client):
    r = client.post("/api/games/import", json={"data": {"version": 99, "players": []}})
    assert r.status_code == 400

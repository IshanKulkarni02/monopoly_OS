def _setup_virtual_game(client, **overrides):
    data = client.post("/api/games", json={"host_name": "Alice", "play_mode": "virtual", **overrides}).json()
    code = data["game"]["code"]
    host_id = data["host_player_id"]
    host_token = data["player_token"]
    client.post(f"/api/games/{code}/join", json={"name": "Bob"})
    client.post(f"/api/games/{code}/start", headers={"x-host-token": data["host_token"]})
    return code, host_id, host_token


def test_dice_source_defaults_to_server(client):
    data = client.post("/api/games", json={"host_name": "Alice"}).json()
    assert data["game"]["ruleset"]["dice_source"] == "server"


def test_server_dice_source_ignores_supplied_dice_and_still_rolls(client):
    code, host_id, host_token = _setup_virtual_game(client)
    r = client.post(
        f"/api/games/{code}/roll",
        json={"dice": [6, 6]},
        headers={"x-player-id": host_id, "x-player-token": host_token},
    )
    assert r.status_code == 200, r.text
    # dice_source stayed "server" so the roll is randomized, not forced to [6, 6] —
    # position should reflect *some* valid roll, not necessarily 12.
    assert r.json()["result"]["outcome"] in ("moved", "stayed_in_jail")


def test_manual_dice_source_requires_dice_and_uses_exact_values(client):
    code, host_id, host_token = _setup_virtual_game(client, dice_source="manual")
    r = client.post(f"/api/games/{code}/roll", json={}, headers={"x-player-id": host_id, "x-player-token": host_token})
    assert r.status_code == 400

    r = client.post(
        f"/api/games/{code}/roll",
        json={"dice": [4, 3]},
        headers={"x-player-id": host_id, "x-player-token": host_token},
    )
    assert r.status_code == 200, r.text
    assert r.json()["result"]["dice"] == [4, 3]
    assert r.json()["result"]["position"] == 7


def test_manual_dice_source_rejects_wrong_dice_count(client):
    code, host_id, host_token = _setup_virtual_game(client, dice_source="manual")
    r = client.post(
        f"/api/games/{code}/roll",
        json={"dice": [4]},
        headers={"x-player-id": host_id, "x-player-token": host_token},
    )
    assert r.status_code == 400

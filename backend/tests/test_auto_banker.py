def _setup_auto_game(client):
    data = client.post("/api/games", json={"host_name": "Alice", "banker_mode": "auto"}).json()
    code = data["game"]["code"]
    host_id = data["host_player_id"]
    host_token = data["host_token"]
    host_player_token = data["player_token"]

    bob = client.post(f"/api/games/{code}/join", json={"name": "Bob"}).json()
    client.post(f"/api/games/{code}/start", headers={"x-host-token": host_token})
    return code, host_id, host_player_token, bob["player_id"], bob["player_token"]


def test_auto_banker_purchase_then_rent(client):
    code, host_id, host_token, bob_id, bob_token = _setup_auto_game(client)

    state = client.get(f"/api/games/{code}").json()
    med_ave = next(p for p in state["properties"] if p["name"] == "Mediterranean Avenue")

    client.post(
        f"/api/games/{code}/properties/{med_ave['id']}/purchase",
        headers={"x-player-id": host_id, "x-player-token": host_token},
    )

    r = client.post(
        f"/api/games/{code}/land",
        json={"player_id": bob_id, "space_index": 1},
        headers={"x-player-token": bob_token},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["outcome"]["outcome"] == "rent_paid"
    assert body["outcome"]["amount"] == 2

    bob_state = next(p for p in body["game"]["players"] if p["id"] == bob_id)
    assert bob_state["balance"] == 1500 - 2


def test_auto_banker_tax_and_unowned(client):
    code, host_id, host_token, bob_id, bob_token = _setup_auto_game(client)

    r = client.post(
        f"/api/games/{code}/land",
        json={"player_id": bob_id, "space_index": 4},
        headers={"x-player-token": bob_token},
    )
    assert r.json()["outcome"]["outcome"] == "tax_paid"
    assert r.json()["outcome"]["amount"] == 200

    r = client.post(
        f"/api/games/{code}/land",
        json={"player_id": bob_id, "space_index": 3},
        headers={"x-player-token": bob_token},
    )
    assert r.json()["outcome"]["outcome"] == "purchasable"


def test_auto_banker_railroad_rent_scales_with_count(client):
    code, host_id, host_token, bob_id, bob_token = _setup_auto_game(client)
    state = client.get(f"/api/games/{code}").json()
    railroads = [p for p in state["properties"] if p["name"] in ("Reading Railroad", "Pennsylvania Railroad")]
    for rr in railroads:
        client.post(
            f"/api/games/{code}/properties/{rr['id']}/purchase",
            headers={"x-player-id": host_id, "x-player-token": host_token},
        )

    r = client.post(
        f"/api/games/{code}/land",
        json={"player_id": bob_id, "space_index": 15},
        headers={"x-player-token": bob_token},
    )
    assert r.json()["outcome"]["outcome"] == "rent_paid"
    assert r.json()["outcome"]["amount"] == 50


def test_auto_banker_utility_needs_dice_roll(client):
    code, host_id, host_token, bob_id, bob_token = _setup_auto_game(client)
    state = client.get(f"/api/games/{code}").json()
    electric = next(p for p in state["properties"] if p["name"] == "Electric Company")
    client.post(
        f"/api/games/{code}/properties/{electric['id']}/purchase",
        headers={"x-player-id": host_id, "x-player-token": host_token},
    )

    r = client.post(
        f"/api/games/{code}/land",
        json={"player_id": bob_id, "space_index": 12},
        headers={"x-player-token": bob_token},
    )
    assert r.json()["outcome"]["outcome"] == "needs_manual"

    r = client.post(
        f"/api/games/{code}/land",
        json={"player_id": bob_id, "space_index": 12, "dice_roll": 7},
        headers={"x-player-token": bob_token},
    )
    assert r.json()["outcome"]["outcome"] == "rent_paid"
    assert r.json()["outcome"]["amount"] == 28  # 4x multiplier, one utility owned


def test_manual_mode_game_rejects_land(client):
    data = client.post("/api/games", json={"host_name": "Alice"}).json()
    code = data["game"]["code"]
    host_token = data["host_token"]
    bob = client.post(f"/api/games/{code}/join", json={"name": "Bob"}).json()
    client.post(f"/api/games/{code}/start", headers={"x-host-token": host_token})

    r = client.post(
        f"/api/games/{code}/land",
        json={"player_id": bob["player_id"], "space_index": 1},
        headers={"x-player-token": bob["player_token"]},
    )
    assert r.status_code == 400

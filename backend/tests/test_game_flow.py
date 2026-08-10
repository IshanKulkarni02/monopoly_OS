def test_create_join_start_and_transact(client):
    r = client.post("/api/games", json={"host_name": "Alice", "name": "Family Night"})
    assert r.status_code == 200
    data = r.json()
    code = data["game"]["code"]
    host_id = data["host_player_id"]
    host_token = data["host_token"]
    host_player_token = data["player_token"]
    assert data["game"]["status"] == "lobby"
    assert data["game"]["players"][0]["balance"] == 1500

    r = client.post(f"/api/games/{code}/join", json={"name": "Bob"})
    assert r.status_code == 200
    bob = r.json()
    bob_id = bob["player_id"]
    bob_token = bob["player_token"]
    assert len(bob["game"]["players"]) == 2

    r = client.post(f"/api/games/{code}/start")
    assert r.status_code == 403

    r = client.post(f"/api/games/{code}/start", headers={"x-host-token": host_token})
    assert r.status_code == 200
    state = r.json()
    assert state["status"] == "active"
    assert len(state["properties"]) == 28

    r = client.post(
        f"/api/games/{code}/transactions",
        json={"from_player_id": None, "to_player_id": bob_id, "amount": 50, "reason": "birthday gift"},
        headers={"x-player-id": host_id, "x-player-token": host_player_token},
    )
    assert r.status_code == 200
    bob_state = next(p for p in r.json()["players"] if p["id"] == bob_id)
    assert bob_state["balance"] == 1550

    r = client.post(
        f"/api/games/{code}/transactions",
        json={"from_player_id": bob_id, "to_player_id": None, "amount": 10, "reason": "tax"},
        headers={"x-player-id": bob_id, "x-player-token": bob_token},
    )
    assert r.status_code == 403


def test_purchase_property_and_insufficient_funds(client):
    data = client.post("/api/games", json={"host_name": "Alice"}).json()
    code = data["game"]["code"]
    host_id = data["host_player_id"]
    host_token = data["host_token"]
    host_player_token = data["player_token"]

    bob = client.post(f"/api/games/{code}/join", json={"name": "Bob"}).json()
    client.post(f"/api/games/{code}/start", headers={"x-host-token": host_token})

    state = client.get(f"/api/games/{code}").json()
    boardwalk = next(p for p in state["properties"] if p["name"] == "Boardwalk")

    r = client.post(
        f"/api/games/{code}/properties/{boardwalk['id']}/purchase",
        headers={"x-player-id": host_id, "x-player-token": host_player_token},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["purchased"] is True
    state = body["game"]
    host_state = next(p for p in state["players"] if p["id"] == host_id)
    assert host_state["balance"] == 1500 - 400
    boardwalk_after = next(p for p in state["properties"] if p["name"] == "Boardwalk")
    assert boardwalk_after["owner_id"] == host_id

    r = client.post(
        f"/api/games/{code}/properties/{boardwalk['id']}/purchase",
        headers={"x-player-id": bob["player_id"], "x-player-token": bob["player_token"]},
    )
    assert r.status_code == 400


def test_reverse_transaction(client):
    data = client.post("/api/games", json={"host_name": "Alice"}).json()
    code = data["game"]["code"]
    host_id = data["host_player_id"]
    host_token = data["host_token"]
    host_player_token = data["player_token"]
    client.post(f"/api/games/{code}/join", json={"name": "Bob"})
    client.post(f"/api/games/{code}/start", headers={"x-host-token": host_token})

    state = client.get(f"/api/games/{code}").json()
    bob_id = next(p["id"] for p in state["players"] if p["name"] == "Bob")

    client.post(
        f"/api/games/{code}/transactions",
        json={"from_player_id": host_id, "to_player_id": bob_id, "amount": 100, "reason": "oops"},
        headers={"x-player-id": host_id, "x-player-token": host_player_token},
    )

    log = client.get(f"/api/games/{code}/players/{host_id}/log").json()
    txn_event = next(e for e in log if e["kind"] == "transaction" and e["payload"]["amount"] == 100)
    txn_id = txn_event["payload"]["transaction_id"]

    r = client.post(
        f"/api/games/{code}/transactions/{txn_id}/reverse",
        headers={"x-player-id": host_id, "x-player-token": host_player_token},
    )
    assert r.status_code == 200
    host_state = next(p for p in r.json()["players"] if p["id"] == host_id)
    assert host_state["balance"] == 1500

    # can't double-reverse
    r = client.post(
        f"/api/games/{code}/transactions/{txn_id}/reverse",
        headers={"x-player-id": host_id, "x-player-token": host_player_token},
    )
    assert r.status_code == 400


def test_multi_game_isolation(client):
    r1 = client.post("/api/games", json={"host_name": "Alice"}).json()
    r2 = client.post("/api/games", json={"host_name": "Zed"}).json()
    assert r1["game"]["code"] != r2["game"]["code"]

    client.post(f"/api/games/{r1['game']['code']}/join", json={"name": "Bob"})

    state1 = client.get(f"/api/games/{r1['game']['code']}").json()
    state2 = client.get(f"/api/games/{r2['game']['code']}").json()
    assert len(state1["players"]) == 2
    assert len(state2["players"]) == 1

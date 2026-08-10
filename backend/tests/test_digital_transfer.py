def _setup_transfer_game(client):
    data = client.post("/api/games", json={"host_name": "Alice", "money_mode": "digital_transfer"}).json()
    code = data["game"]["code"]
    host_id = data["host_player_id"]
    host_player_token = data["player_token"]
    bob = client.post(f"/api/games/{code}/join", json={"name": "Bob"}).json()
    client.post(f"/api/games/{code}/start", headers={"x-host-token": data["host_token"]})
    return code, host_id, host_player_token, bob["player_id"], bob["player_token"]


def test_send_is_immediate_and_self_authorized(client):
    code, alice_id, alice_token, bob_id, bob_token = _setup_transfer_game(client)

    r = client.post(
        f"/api/games/{code}/transfer/send",
        json={"other_player_id": bob_id, "amount": 100, "reason": "movie tickets"},
        headers={"x-player-id": alice_id, "x-player-token": alice_token},
    )
    assert r.status_code == 200
    state = r.json()
    alice_state = next(p for p in state["players"] if p["id"] == alice_id)
    bob_state = next(p for p in state["players"] if p["id"] == bob_id)
    assert alice_state["balance"] == 1400
    assert bob_state["balance"] == 1600
    assert state["pending_transfers"] == []


def test_request_needs_payer_confirmation(client):
    code, alice_id, alice_token, bob_id, bob_token = _setup_transfer_game(client)

    r = client.post(
        f"/api/games/{code}/transfer/request",
        json={"other_player_id": bob_id, "amount": 75, "reason": "rent"},
        headers={"x-player-id": alice_id, "x-player-token": alice_token},
    )
    assert r.status_code == 200
    state = r.json()
    assert len(state["pending_transfers"]) == 1
    txn_id = state["pending_transfers"][0]["id"]
    # balances untouched until Bob confirms
    assert next(p for p in state["players"] if p["id"] == alice_id)["balance"] == 1500
    assert next(p for p in state["players"] if p["id"] == bob_id)["balance"] == 1500

    # Alice can't confirm her own request against Bob's money
    r = client.post(
        f"/api/games/{code}/transfer/{txn_id}/confirm",
        headers={"x-player-id": alice_id, "x-player-token": alice_token},
    )
    assert r.status_code == 403

    r = client.post(
        f"/api/games/{code}/transfer/{txn_id}/confirm",
        headers={"x-player-id": bob_id, "x-player-token": bob_token},
    )
    assert r.status_code == 200
    state = r.json()
    assert next(p for p in state["players"] if p["id"] == alice_id)["balance"] == 1575
    assert next(p for p in state["players"] if p["id"] == bob_id)["balance"] == 1425
    assert state["pending_transfers"] == []


def test_request_can_be_declined(client):
    code, alice_id, alice_token, bob_id, bob_token = _setup_transfer_game(client)

    state = client.post(
        f"/api/games/{code}/transfer/request",
        json={"other_player_id": bob_id, "amount": 75, "reason": "rent"},
        headers={"x-player-id": alice_id, "x-player-token": alice_token},
    ).json()
    txn_id = state["pending_transfers"][0]["id"]

    r = client.post(
        f"/api/games/{code}/transfer/{txn_id}/decline",
        headers={"x-player-id": bob_id, "x-player-token": bob_token},
    )
    assert r.status_code == 200
    state = r.json()
    assert state["pending_transfers"] == []
    assert next(p for p in state["players"] if p["id"] == bob_id)["balance"] == 1500

    # can't confirm/decline an already-resolved request
    r = client.post(
        f"/api/games/{code}/transfer/{txn_id}/confirm",
        headers={"x-player-id": bob_id, "x-player-token": bob_token},
    )
    assert r.status_code == 400


def test_transfer_endpoints_require_digital_transfer_mode(client):
    data = client.post("/api/games", json={"host_name": "Alice"}).json()  # default banker_ledger mode
    code = data["game"]["code"]
    bob = client.post(f"/api/games/{code}/join", json={"name": "Bob"}).json()
    client.post(f"/api/games/{code}/start", headers={"x-host-token": data["host_token"]})

    r = client.post(
        f"/api/games/{code}/transfer/send",
        json={"other_player_id": bob["player_id"], "amount": 10, "reason": ""},
        headers={"x-player-id": data["host_player_id"], "x-player-token": data["player_token"]},
    )
    assert r.status_code == 400
